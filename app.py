import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import re
from datetime import datetime, time

st.set_page_config(page_title="Тепловая карта кабинетов", layout="wide")

# ==================== МАППИНГ СПЕЦИАЛИЗАЦИЙ ====================
# Цвет ячейки = специализация. Текст поверх = фамилия врача.
# Вы можете отредактировать эти словари под свою клинику.

CABINET_TO_SPEC = {
    '1': 'Терапия',
    '2': 'Терапия',
    '3': 'Функц. диагностика',
    '4': 'Терапия',
    '5': 'Лаборатория',
    '6': 'Терапия',
    '7': 'Терапия',
    '8': 'Терапия',
    '9': 'Рентген',
    '10': 'Терапия',
    '12': 'Дневной стационар',
    '13': 'Терапия',
    '14': 'Терапия',
    '15': 'Терапия',
    '17': 'Терапия',
    '18': 'Терапия',
    '19': 'Терапия',
    '20': 'Терапия',
    '21': 'Терапия',
    '22': 'Хирургия',
    '23': 'Хирургия',
    '24': 'Терапия',
    '25': 'Хирургия',
    '': 'Прочее',
}

DOCTOR_TO_SPEC = {
    'Дневной стационар': 'Дневной стационар',
    'Кабинет забора биоматериала': 'Лаборатория',
    'Кабинет забора мазков': 'Лаборатория',
    'Кабинет описания Холтеров и СМАДов': 'Функц. диагностика',
    'Кабинет описания ЭКГ .': 'Функц. диагностика',
    'Кабинет описания спирографии': 'Функц. диагностика',
    'Кабинет повторных приемов': 'Терапия',
    'Кабинет физиотерапии': 'Физиотерапия',
    'Операционная . .': 'Хирургия',
    'Перевязочная хирургия .': 'Хирургия',
    'Рентген Кабинет .': 'Рентген',
    'Травмпункт Перевязочная Северная': 'Хирургия',
}

SPEC_COLORS = {
    'Терапия': '#2E86AB',
    'Хирургия': '#E94F37',
    'Рентген': '#F6AE2D',
    'Лаборатория': '#86BBD8',
    'Функц. диагностика': '#9B5DE5',
    'Дневной стационар': '#F15BB5',
    'Физиотерапия': '#00BBF9',
    'Прочее': '#CCCCCC',
}

SPEC_ORDER = ['Терапия', 'Хирургия', 'Рентген', 'Лаборатория',
              'Функц. диагностика', 'Дневной стационар', 'Физиотерапия', 'Прочее']


# ==================== ФУНКЦИИ ПАРСИНГА ====================
def parse_period(period_str):
    if pd.isna(period_str) or period_str == '':
        return None, None
    match = re.match(r'(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})', str(period_str))
    if match:
        h1, m1, h2, m2 = map(int, match.groups())
        return time(h1, m1), time(h2, m2)
    return None, None


def parse_excel(uploaded_file):
    df_raw = pd.read_excel(uploaded_file, sheet_name=0, header=None)
    records = []
    current_doctor = None

    for idx, row in df_raw.iterrows():
        if idx < 8:
            continue
        val0 = str(row[0]) if pd.notna(row[0]) else ""
        if "Отображаемые в расписании" in val0:
            continue
        date_match = re.match(r'^(\d{2})\.(\d{2})\.(\d{4})$', val0.strip())
        if date_match:
            if current_doctor is None:
                continue
            records.append({
                'doctor': current_doctor,
                'date': val0.strip(),
                'period': str(row[1]) if pd.notna(row[1]) else "",
                'cabinet': str(row[2]) if pd.notna(row[2]) else "",
                'hours_tab': float(row[3]) if pd.notna(row[3]) else 0,
            })
        else:
            if (val0.strip() and val0.strip() not in ['nan', 'Доктор']
                    and not val0.strip().startswith('С:')
                    and not val0.strip().startswith('ПО:')
                    and not val0.strip().startswith('Клиника')):
                if not re.match(r'^\d{2}\.\d{2}\.\d{4}$', val0.strip()):
                    current_doctor = val0.strip()

    df = pd.DataFrame(records)
    df['start_time'], df['end_time'] = zip(*df['period'].apply(parse_period))
    df['date_parsed'] = pd.to_datetime(df['date'], format='%d.%m.%Y')
    df['date_short'] = df['date_parsed'].dt.strftime('%d.%m')
    df['day_name'] = df['date_parsed'].dt.day_name()
    return df


def assign_specializations(df):
    """Назначает каждому врачу специализацию"""
    # Для врачей из DOCTOR_TO_SPEC
    df['spec'] = df['doctor'].map(DOCTOR_TO_SPEC)

    # Для остальных — по основному кабинету
    mask = df['spec'].isna()
    if mask.any():
        # Находим основной кабинет для каждого врача
        doc_cab = (df[mask].groupby(['doctor', 'cabinet'])['hours_tab']
                          .sum().reset_index())
        doc_main = doc_cab.loc[doc_cab.groupby('doctor')['hours_tab'].idxmax()]
        main_cab_map = dict(zip(doc_main['doctor'], doc_main['cabinet']))

        def get_spec(row):
            if pd.notna(row['spec']):
                return row['spec']
            cab = main_cab_map.get(row['doctor'], '')
            return CABINET_TO_SPEC.get(cab, 'Прочее')

        df['spec'] = df.apply(get_spec, axis=1)

    return df


def get_surname(full_name):
    """Извлекает фамилию из полного имени"""
    if pd.isna(full_name):
        return ''
    parts = str(full_name).strip().split()
    return parts[0] if parts else str(full_name)


# ==================== ВИЗУАЛИЗАЦИИ ====================
def create_overview_heatmap(df, selected_cabinets, selected_dates):
    df_f = df[df['cabinet'].isin(selected_cabinets) &
              df['date_short'].isin(selected_dates)].copy()

    if df_f.empty:
        return go.Figure().update_layout(title="Нет данных для отображения")

    all_dates = sorted(selected_dates)
    all_cabs = sorted(selected_cabinets, key=lambda x: int(x) if x.isdigit() else 999)

    # Агрегируем: для каждой ячейки (дата, кабинет) — список врачей и их специализаций
    grouped = df_f.groupby(['date_short', 'cabinet']).agg({
        'doctor': lambda x: sorted(x.unique()),
        'spec': lambda x: x.mode().iloc[0] if not x.mode().empty else 'Прочее',
        'hours_tab': 'sum',
    }).reset_index()

    # Полная сетка
    grid = pd.DataFrame([(d, c) for d in all_dates for c in all_cabs],
                        columns=['date_short', 'cabinet'])
    grid = grid.merge(grouped, on=['date_short', 'cabinet'], how='left')
    grid['spec'] = grid['spec'].fillna('Прочее')
    grid['doctor'] = grid['doctor'].apply(lambda x: x if isinstance(x, list) else [])

    # Текст для ячеек — фамилии врачей
    def make_text(doctors):
        if not doctors:
            return 'Пусто'
        surnames = [get_surname(d) for d in doctors]
        txt = ', '.join(surnames)
        return txt if len(txt) <= 18 else txt[:15] + '…'

    grid['cell_text'] = grid['doctor'].apply(make_text)

    # Числовой код для цвета = индекс специализации
    spec_to_code = {s: i for i, s in enumerate(SPEC_ORDER)}
    grid['code'] = grid['spec'].map(spec_to_code).fillna(len(SPEC_ORDER) - 1)

    pivot_codes = grid.pivot(index='cabinet', columns='date_short', values='code')
    pivot_codes = pivot_codes.reindex(index=all_cabs, columns=all_dates)
    pivot_text = grid.pivot(index='cabinet', columns='date_short', values='cell_text')
    pivot_text = pivot_text.reindex(index=all_cabs, columns=all_dates).fillna('Пусто')
    pivot_spec = grid.pivot(index='cabinet', columns='date_short', values='spec')
    pivot_spec = pivot_spec.reindex(index=all_cabs, columns=all_dates).fillna('Прочее')

    # Цветовая шкала (дискретная)
    colorscale = []
    n = len(SPEC_ORDER)
    for i, spec in enumerate(SPEC_ORDER):
        pos = i / max(n - 1, 1)
        colorscale.append([pos, SPEC_COLORS[spec]])

    fig = go.Figure(data=go.Heatmap(
        z=pivot_codes.values,
        x=pivot_codes.columns,
        y=pivot_codes.index,
        text=pivot_text.values,
        texttemplate='%{text}',
        textfont={'size': 10, 'color': 'white'},
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
        title='📅 Обзорная тепловая карта: цвет = специализация, текст = врач',
        xaxis_title='Дата',
        yaxis_title='Кабинет',
        height=max(500, len(all_cabs) * 40),
        width=max(900, len(all_dates) * 110),
        yaxis={'categoryorder': 'array', 'categoryarray': all_cabs[::-1]},
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(size=12),
    )
    return fig


def create_hourly_heatmap(df, selected_date, selected_cabinets):
    df_day = df[(df['date'] == selected_date) &
                (df['cabinet'].isin(selected_cabinets))].copy()

    if df_day.empty:
        return go.Figure().update_layout(title="Нет данных для отображения")

    hours = []
    for h in range(7, 24):
        hours.append(f"{h:02d}:00")
        hours.append(f"{h:02d}:30")

    def time_to_minutes(t):
        if t is None:
            return None
        return t.hour * 60 + t.minute

    def is_working(row, time_str):
        if pd.isna(row['start_time']) or pd.isna(row['end_time']):
            return False
        h, m = map(int, time_str.split(':'))
        minutes = h * 60 + m
        start = time_to_minutes(row['start_time'])
        end = time_to_minutes(row['end_time'])
        return start <= minutes < end

    all_cabs = sorted(selected_cabinets, key=lambda x: int(x) if x.isdigit() else 999)
    spec_to_code = {s: i for i, s in enumerate(SPEC_ORDER)}

    colorscale = []
    n = len(SPEC_ORDER)
    for i, spec in enumerate(SPEC_ORDER):
        pos = i / max(n - 1, 1)
        colorscale.append([pos, SPEC_COLORS[spec]])

    z_matrix = []
    text_matrix = []
    spec_matrix = []

    for cab in all_cabs:
        cab_df = df_day[df_day['cabinet'] == cab]
        z_row, text_row, spec_row = [], [], []
        for h in hours:
            docs = []
            specs = []
            for _, r in cab_df.iterrows():
                if is_working(r, h):
                    docs.append(r['doctor'])
                    specs.append(r['spec'])
            if docs:
                # Берём первого врача и его специализацию
                doc = docs[0]
                spec = specs[0]
                z_row.append(spec_to_code.get(spec, n - 1))
                text_row.append(get_surname(doc))
                spec_row.append(spec)
            else:
                z_row.append(spec_to_code.get('Прочее', n - 1))
                text_row.append('Пусто')
                spec_row.append('Прочее')
        z_matrix.append(z_row)
        text_matrix.append(text_row)
        spec_matrix.append(spec_row)

    fig = go.Figure(data=go.Heatmap(
        z=z_matrix,
        x=hours,
        y=all_cabs,
        text=text_matrix,
        texttemplate='%{text}',
        textfont={'size': 8, 'color': 'white'},
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
        height=max(500, len(all_cabs) * 40),
        width=1400,
        yaxis={'categoryorder': 'array', 'categoryarray': all_cabs[::-1]},
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(size=12),
    )
    return fig


# ==================== ОСНОВНОЕ ПРИЛОЖЕНИЕ ====================
def main():
    st.markdown("# 🏥 Тепловая карта загрузки кабинетов")
    st.markdown(
        "<p style='color:#666; font-size:1.1rem;'>"
        "Цвет ячейки = <b>специализация</b> &nbsp;|&nbsp; "
        "Текст в ячейке = <b>фамилия врача</b>"
        "</p>",
        unsafe_allow_html=True,
    )

    uploaded_file = st.file_uploader("📁 Загрузите отчёт Excel", type=['xlsx', 'xls'])

    if uploaded_file is None:
        st.info("👆 Загрузите Excel-файл с отчётом о загрузке врачей.")
        st.markdown("""
        **Ожидаемый формат:**
        - Колонки: Доктор | Период | Кабинет | Часов по табелю | …
        - Строки с датами в формате `DD.MM.YYYY`
        """)
        return

    with st.spinner('⏳ Парсинг данных…'):
        df = parse_excel(uploaded_file)
        df = assign_specializations(df)

    if df.empty:
        st.error("❌ Не удалось распознать данные. Проверьте формат файла.")
        return

    # Метрики
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("👨‍⚕️ Врачей", df['doctor'].nunique())
    with c2:
        st.metric("🚪 Кабинетов", df['cabinet'].nunique())
    with c3:
        st.metric("📅 Дней", df['date_short'].nunique())
    with c4:
        specs = df['spec'].unique()
        st.metric("🩺 Специальностей", len(specs))
    with c5:
        st.metric("📝 Записей", len(df))

    st.divider()

    # ===== БОКОВАЯ ПАНЕЛЬ =====
    with st.sidebar:
        st.header("⚙️ Фильтры")

        mode = st.radio(
            "Режим:",
            ["📅 Обзор по дням", "⏰ Детально по часам"],
            index=0,
        )

        all_cabinets = sorted(
            [c for c in df['cabinet'].unique() if c != ''],
            key=lambda x: int(x) if x.isdigit() else 999,
        )
        selected_cabinets = st.multiselect("Кабинеты:", all_cabinets, default=all_cabinets)

        if not selected_cabinets:
            st.warning("Выберите хотя бы один кабинет")
            return

        all_dates = sorted(df['date_short'].unique())

        if mode == "📅 Обзор по дням":
            date_opt = st.radio(
                "Диапазон:",
                ["Все дни", "Последние 7 дней", "Выбрать вручную"],
                index=1,
            )
            if date_opt == "Все дни":
                selected_dates = all_dates
            elif date_opt == "Последние 7 дней":
                selected_dates = all_dates[-7:] if len(all_dates) >= 7 else all_dates
            else:
                selected_dates = st.multiselect("Даты:", all_dates, default=all_dates[:7])
        else:
            selected_date = st.selectbox(
                "Дата:",
                sorted(df['date'].unique(),
                       key=lambda x: datetime.strptime(x, '%d.%m.%Y')),
            )
            selected_dates = [selected_date]

        st.divider()
        st.markdown("**🩺 Специализации:**")
        for spec in SPEC_ORDER:
            if spec in df['spec'].values:
                color = SPEC_COLORS[spec]
                st.markdown(
                    f"<span style='display:inline-block; width:14px; height:14px; "
                    f"background:{color}; border-radius:3px; margin-right:6px;'></span>{spec}",
                    unsafe_allow_html=True,
                )

    # ===== ОСНОВНАЯ ОБЛАСТЬ =====
    if mode == "📅 Обзор по дням":
        st.subheader("📅 Обзорная тепловая карта")
        fig = create_overview_heatmap(df, selected_cabinets, selected_dates)
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("📊 Таблица данных"):
            show = df[df['cabinet'].isin(selected_cabinets) &
                      df['date_short'].isin(selected_dates)][
                ['date', 'doctor', 'spec', 'cabinet', 'period', 'hours_tab']
            ].sort_values(['date', 'cabinet', 'start_time'])
            st.dataframe(show, use_container_width=True, hide_index=True)
    else:
        st.subheader(f"⏰ Почасовая карта — {selected_date}")
        fig = create_hourly_heatmap(df, selected_date, selected_cabinets)
        st.plotly_chart(fig, use_container_width=True)

        df_day = df[df['date'] == selected_date]
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Работающих врачей", df_day['doctor'].nunique())
        with c2:
            st.metric("Занятых кабинетов", df_day['cabinet'].nunique())
        with c3:
            st.metric("Всего часов", round(df_day['hours_tab'].sum(), 1))


if __name__ == "__main__":
    main()
