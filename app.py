import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, time
import re

st.set_page_config(page_title="Тепловая карта кабинетов", layout="wide")

# ==================== НОРМАЛИЗАЦИЯ СПЕЦИАЛИЗАЦИЙ ====================
SPEC_MAP = {
    'терапевт': 'Терапия',
    'кардиолог': 'Кардиология',
    'эндокринолог': 'Эндокринология',
    'невролог': 'Неврология',
    'хирургия': 'Хирургия',
    'хирург': 'Хирургия',
    'травматолог': 'Травматология',
    'ортопед': 'Травматология',
    'рентгенолог': 'Рентген',
    'рентген': 'Рентген',
    'ультразвуковой': 'УЗИ',
    'уздг': 'УЗИ',
    'функциональной диагностики': 'Функц. диагностика',
    'гинеколог': 'Гинекология',
    'акушер': 'Гинекология',
    'уролог': 'Урология',
    'дерматовенеролог': 'Дерматология',
    'онколог': 'Онкология',
    'флеболог': 'Флебология',
    'гастроэнтеролог': 'Гастроэнтерология',
    'отоларинголог': 'ЛОР',
    'колопроктолог': 'Колопроктология',
    'психолог': 'Психология',
    'процедурные кабинеты': 'Процедурные',
    'лаборатория': 'Лаборатория',
    'статистик': 'Администрация',
    'дневной стационар': 'Стационар',
}

BASE_COLORS = {
    'Терапия': '#2E86AB',
    'Кардиология': '#A23B72',
    'Эндокринология': '#F18F01',
    'Неврология': '#C73E1D',
    'Хирургия': '#E94F37',
    'Травматология': '#F6AE2D',
    'Рентген': '#6A4C93',
    'УЗИ': '#9B5DE5',
    'Функц. диагностика': '#00BBF9',
    'Гинекология': '#F15BB5',
    'Урология': '#3A86FF',
    'Дерматология': '#8338EC',
    'Онкология': '#FB5607',
    'Флебология': '#FF006E',
    'Гастроэнтерология': '#3A0CA3',
    'ЛОР': '#4361EE',
    'Колопроктология': '#7209B7',
    'Психология': '#4CC9F0',
    'Процедурные': '#86BBD8',
    'Лаборатория': '#06D6A0',
    'Администрация': '#95A5A6',
    'Стационар': '#118AB2',
    'Прочее': '#BDC3C7',
    'Пусто': '#ECECEC',
}

EXTRA_PALETTE = [
    '#264653', '#2a9d8f', '#e9c46a', '#f4a261', '#e76f51',
    '#8ac926', '#1982c4', '#ffca3a', '#ff595e', '#8d99ae',
    '#d62828', '#f77f00', '#fcbf49', '#eae2b7', '#003049',
]


def normalize_spec(raw):
    if pd.isna(raw):
        return 'Прочее'
    s = str(raw).strip().lower()
    for key, val in SPEC_MAP.items():
        if key in s:
            return val
    return 'Прочее'


def get_surname(full_name):
    if pd.isna(full_name):
        return ''
    parts = str(full_name).strip().split()
    return parts[0] if parts else str(full_name)


def assign_colors(all_specs):
    colors = {}
    extra_idx = 0
    for spec in sorted(all_specs):
        if spec in BASE_COLORS:
            colors[spec] = BASE_COLORS[spec]
        else:
            colors[spec] = EXTRA_PALETTE[extra_idx % len(EXTRA_PALETTE)]
            extra_idx += 1
    return colors


# ==================== ПАРСИНГ ====================
def parse_excel_new(uploaded_file):
    # Новый отчёт: заголовки на 7-й строке (индекс 6)
    df = pd.read_excel(uploaded_file, sheet_name=0, header=6)
    # Приводим имена колонок
    df.columns = ['Кабинет', 'Дата', 'Период', 'Доктор', 'Специализация']
    # Убираем строки без даты или периода
    df = df.dropna(subset=['Дата', 'Период']).copy()

    # Нормализуем кабинет: если пустой — берём название из Доктора
    def fix_cabinet(row):
        cab = row['Кабинет']
        if pd.isna(cab) or str(cab).strip() == '':
            return str(row['Доктор']).strip()
        try:
            return str(int(float(cab)))
        except:
            return str(cab).strip()

    df['Кабинет'] = df.apply(fix_cabinet, axis=1)

    # Дата
    df['date_parsed'] = pd.to_datetime(df['Дата'], format='%d.%m.%Y', errors='coerce')
    df = df.dropna(subset=['date_parsed'])
    df['date_str'] = df['date_parsed'].dt.strftime('%d.%m.%Y')
    df['date_short'] = df['date_parsed'].dt.strftime('%d.%m')
    df['weekday'] = df['date_parsed'].dt.strftime('%a')

    # Период → start_time, end_time
    def parse_period(p):
        m = re.match(r'(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})', str(p))
        if m:
            h1, m1, h2, m2 = map(int, m.groups())
            return time(h1, m1), time(h2, m2)
        return None, None

    df[['start_time', 'end_time']] = df['Период'].apply(
        lambda x: pd.Series(parse_period(x))
    )

    # Специализация
    df['spec'] = df['Специализация'].apply(normalize_spec)

    # Фамилия
    df['surname'] = df['Доктор'].apply(get_surname)

    # Часы
    def calc_hours(row):
        if pd.notna(row['start_time']) and pd.notna(row['end_time']):
            s = row['start_time'].hour * 60 + row['start_time'].minute
            e = row['end_time'].hour * 60 + row['end_time'].minute
            return max(0, (e - s) / 60)
        return 0

    df['hours'] = df.apply(calc_hours, axis=1)
    return df


# ==================== ВИЗУАЛИЗАЦИИ ====================
def cabinet_sort_key(c):
    try:
        return (0, int(c))
    except:
        return (1, c)


def create_overview_heatmap(df, selected_cabinets, selected_dates, colors, spec_to_code):
    df_f = df[df['Кабинет'].isin(selected_cabinets) & df['date_short'].isin(selected_dates)].copy()

    all_dates = sorted(selected_dates, key=lambda x: datetime.strptime(x + '.2026', '%d.%m.%Y'))
    all_cabs = sorted(selected_cabinets, key=cabinet_sort_key)

    # Агрегируем по кабинет-дата
    if not df_f.empty:
        agg = df_f.groupby(['date_short', 'Кабинет']).agg({
            'spec': lambda x: x.mode().iloc[0] if not x.mode().empty else 'Прочее',
            'surname': lambda x: ', '.join(dict.fromkeys(x)),  # уникальные, сохраняя порядок
            'hours': 'sum',
        }).reset_index()
    else:
        agg = pd.DataFrame(columns=['date_short', 'Кабинет', 'spec', 'surname', 'hours'])

    # Полная сетка
    grid = pd.DataFrame([(d, c) for d in all_dates for c in all_cabs],
                        columns=['date_short', 'Кабинет'])
    grid = grid.merge(agg, on=['date_short', 'Кабинет'], how='left')
    grid['spec'] = grid['spec'].fillna('Пусто')
    grid['surname'] = grid['surname'].fillna('Пусто')

    # Обрезаем длинные строки фамилий
    def truncate(txt):
        if pd.isna(txt):
            return 'Пусто'
        t = str(txt)
        return t if len(t) <= 16 else t[:13] + '…'

    grid['cell_text'] = grid['surname'].apply(truncate)
    grid['code'] = grid['spec'].map(lambda s: spec_to_code.get(s, spec_to_code['Пусто']))

    pivot_code = grid.pivot(index='Кабинет', columns='date_short', values='code')
    pivot_code = pivot_code.reindex(index=all_cabs, columns=all_dates)
    pivot_text = grid.pivot(index='Кабинет', columns='date_short', values='cell_text')
    pivot_text = pivot_text.reindex(index=all_cabs, columns=all_dates).fillna('Пусто')
    pivot_spec = grid.pivot(index='Кабинет', columns='date_short', values='spec')
    pivot_spec = pivot_spec.reindex(index=all_cabs, columns=all_dates).fillna('Пусто')

    # Цветовая шкала (дискретная)
    n = len(spec_to_code)
    colorscale = []
    for spec, code in sorted(spec_to_code.items(), key=lambda x: x[1]):
        pos = code / max(n - 1, 1)
        colorscale.append([pos, colors[spec]])

    fig = go.Figure(data=go.Heatmap(
        z=pivot_code.values,
        x=pivot_code.columns,
        y=pivot_code.index,
        text=pivot_text.values,
        texttemplate='%{text}',
        textfont={'size': 11, 'color': 'white'},
        hovertemplate=(
            '<b>Кабинет:</b> %{y}<br>'
            '<b>Дата:</b> %{x}<br>'
            '<b>Специализация:</b> %{customdata}<br>'
            '<b>Врач(и):</b> %{text}<extra></extra>'
        ),
        customdata=pivot_spec.values,
        colorscale=colorscale,
        showscale=False,
        zmin=0,
        zmax=n - 1,
    ))

    fig.update_layout(
        title='📅 Обзорная тепловая карта (цвет = специализация, текст = врач)',
        xaxis_title='Дата',
        yaxis_title='Кабинет',
        height=max(450, len(all_cabs) * 45),
        width=max(800, len(all_dates) * 130),
        yaxis={'categoryorder': 'array', 'categoryarray': all_cabs[::-1]},
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(size=12),
        margin=dict(l=80, r=40, t=60, b=60),
    )
    return fig


def create_hourly_heatmap(df, selected_date, selected_cabinets, colors, spec_to_code):
    df_day = df[(df['date_str'] == selected_date) & df['Кабинет'].isin(selected_cabinets)].copy()

    # Все часы с 7:00 до 23:30, шаг 30 мин
    hours = [f"{h:02d}:{m:02d}" for h in range(7, 24) for m in (0, 30)]
    all_cabs = sorted(selected_cabinets, key=cabinet_sort_key)

    def time_to_min(t):
        if t is None:
            return None
        return t.hour * 60 + t.minute

    def is_working(row, time_str):
        if pd.isna(row['start_time']) or pd.isna(row['end_time']):
            return False
        h, m = map(int, time_str.split(':'))
        minutes = h * 60 + m
        start = time_to_min(row['start_time'])
        end = time_to_min(row['end_time'])
        return start <= minutes < end

    n = len(spec_to_code)
    colorscale = []
    for spec, code in sorted(spec_to_code.items(), key=lambda x: x[1]):
        pos = code / max(n - 1, 1)
        colorscale.append([pos, colors[spec]])

    z_matrix = []
    text_matrix = []
    spec_matrix = []

    for cab in all_cabs:
        cab_df = df_day[df_day['Кабинет'] == cab]
        z_row, text_row, spec_row = [], [], []
        for h in hours:
            docs = []
            specs = []
            for _, r in cab_df.iterrows():
                if is_working(r, h):
                    docs.append(r['surname'])
                    specs.append(r['spec'])
            if docs:
                # Уникальные фамилии
                unique_docs = list(dict.fromkeys(docs))
                txt = ', '.join(unique_docs)
                if len(txt) > 14:
                    txt = txt[:11] + '…'
                z_row.append(spec_to_code.get(specs[0], spec_to_code['Пусто']))
                text_row.append(txt)
                spec_row.append(specs[0])
            else:
                z_row.append(spec_to_code['Пусто'])
                text_row.append('Пусто')
                spec_row.append('Пусто')
        z_matrix.append(z_row)
        text_matrix.append(text_row)
        spec_matrix.append(spec_row)

    fig = go.Figure(data=go.Heatmap(
        z=z_matrix,
        x=hours,
        y=all_cabs,
        text=text_matrix,
        texttemplate='%{text}',
        textfont={'size': 9, 'color': 'white'},
        hovertemplate=(
            '<b>Кабинет:</b> %{y}<br>'
            '<b>Время:</b> %{x}<br>'
            '<b>Специализация:</b> %{customdata}<br>'
            '<b>Врач:</b> %{text}<extra></extra>'
        ),
        customdata=spec_matrix,
        colorscale=colorscale,
        showscale=False,
        zmin=0,
        zmax=n - 1,
    ))

    fig.update_layout(
        title=f'⏰ Почасовая карта — {selected_date}',
        xaxis_title='Время',
        yaxis_title='Кабинет',
        height=max(500, len(all_cabs) * 45),
        width=1400,
        yaxis={'categoryorder': 'array', 'categoryarray': all_cabs[::-1]},
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(size=12),
        margin=dict(l=80, r=40, t=60, b=60),
    )
    return fig


# ==================== ПРИЛОЖЕНИЕ ====================
def main():
    st.markdown("# 🏥 Тепловая карта загрузки кабинетов")
    st.markdown(
        "<p style='color:#666; font-size:1.05rem;'>"
        "Цвет ячейки = <b>специализация</b> &nbsp;|&nbsp; "
        "Текст = <b>фамилия врача</b> &nbsp;|&nbsp; "
        "Серый = <b>Пусто</b>"
        "</p>",
        unsafe_allow_html=True,
    )

    uploaded_file = st.file_uploader("📁 Загрузите отчёт Excel (cabinets.xlsx)", type=['xlsx', 'xls'])

    if uploaded_file is None:
        st.info("👆 Загрузите файл с отчётом о загрузке кабинетов.")
        st.markdown("""
        **Ожидаемый формат (начиная с 7-й строки):**
        | Кабинет | Дата | Период | Доктор | Специализация |
        """)
        return

    with st.spinner('⏳ Читаем и обрабатываем данные…'):
        df = parse_excel_new(uploaded_file)

    if df.empty:
        st.error("❌ Не удалось распознать данные. Проверьте формат файла.")
        return

    # Цвета
    all_specs = sorted(df['spec'].unique())
    if 'Пусто' not in all_specs:
        all_specs = ['Пусто'] + all_specs
    colors = assign_colors(all_specs)
    spec_to_code = {s: i for i, s in enumerate(sorted(all_specs, key=lambda x: list(colors.keys()).index(x) if x in colors else 999))}

    # Метрики
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("👨‍⚕️ Врачей", df['Доктор'].nunique())
    with c2:
        st.metric("🚪 Кабинетов", df['Кабинет'].nunique())
    with c3:
        st.metric("📅 Дней", df['date_short'].nunique())
    with c4:
        st.metric("📝 Записей", len(df))

    st.divider()

    # ===== БОКОВАЯ ПАНЕЛЬ =====
    with st.sidebar:
        st.header("⚙️ Фильтры")

        mode = st.radio("Режим:", ["📅 Обзор по дням", "⏰ Детально по часам"], index=0)

        all_cabinets = sorted(df['Кабинет'].unique(), key=cabinet_sort_key)
        selected_cabinets = st.multiselect("Кабинеты:", all_cabinets, default=all_cabinets)

        if not selected_cabinets:
            st.warning("Выберите хотя бы один кабинет")
            return

        all_dates_full = sorted(df['date_str'].unique(),
                                key=lambda x: datetime.strptime(x, '%d.%m.%Y'))
        all_dates_short = sorted(df['date_short'].unique(),
                                 key=lambda x: datetime.strptime(x + '.2026', '%d.%m.%Y'))

        if mode == "📅 Обзор по дням":
            date_opt = st.radio("Диапазон:", ["Последние 7 дней", "Все дни", "Выбрать вручную"], index=0)
            if date_opt == "Все дни":
                selected_dates = all_dates_short
            elif date_opt == "Последние 7 дней":
                selected_dates = all_dates_short[-7:] if len(all_dates_short) >= 7 else all_dates_short
            else:
                selected_dates = st.multiselect("Даты:", all_dates_short, default=all_dates_short[:7])
            selected_date = None
        else:
            selected_date = st.selectbox("Дата:", all_dates_full)
            selected_dates = []

        st.divider()
        st.markdown("**🩺 Легенда:**")
        for spec in sorted(spec_to_code.keys()):
            if spec == 'Пусто':
                continue
            color = colors.get(spec, '#999')
            st.markdown(
                f"<span style='display:inline-block; width:12px; height:12px; "
                f"background:{color}; border-radius:2px; margin-right:6px;'></span>{spec}",
                unsafe_allow_html=True,
            )
        st.markdown(
            f"<span style='display:inline-block; width:12px; height:12px; "
            f"background:{colors['Пусто']}; border-radius:2px; margin-right:6px;'></span>Пусто",
            unsafe_allow_html=True,
        )

    # ===== ОСНОВНАЯ ОБЛАСТЬ =====
    if mode == "📅 Обзор по дням":
        if len(selected_dates) > 7:
            st.warning("⚠️ Для обзора отображается максимум 7 дней. Показаны последние 7 выбранных.")
            selected_dates = sorted(selected_dates, key=lambda x: datetime.strptime(x + '.2026', '%d.%m.%Y'))[-7:]

        st.subheader(f"📅 Обзор с {selected_dates[0]} по {selected_dates[-1]} ({len(selected_dates)} дн.)")
        fig = create_overview_heatmap(df, selected_cabinets, selected_dates, colors, spec_to_code)
        st.plotly_chart(fig, use_container_width=False)

        with st.expander("📊 Таблица данных"):
            show = df[df['Кабинет'].isin(selected_cabinets) & df['date_short'].isin(selected_dates)][
                ['date_str', 'Кабинет', 'Доктор', 'spec', 'Период', 'hours']
            ].sort_values(['date_str', 'Кабинет', 'start_time'])
            st.dataframe(show, use_container_width=True, hide_index=True)
    else:
        st.subheader(f"⏰ Почасовая карта — {selected_date}")
        fig = create_hourly_heatmap(df, selected_date, selected_cabinets, colors, spec_to_code)
        st.plotly_chart(fig, use_container_width=False)

        df_day = df[df['date_str'] == selected_date]
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Работающих врачей", df_day['Доктор'].nunique())
        with c2:
            st.metric("Занятых кабинетов", df_day['Кабинет'].nunique())
        with c3:
            st.metric("Всего часов", round(df_day['hours'].sum(), 1))

        with st.expander("📊 Таблица данных за день"):
            show = df_day[df_day['Кабинет'].isin(selected_cabinets)][
                ['Кабинет', 'Доктор', 'spec', 'Период', 'hours']
            ].sort_values(['Кабинет', 'start_time'])
            st.dataframe(show, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
