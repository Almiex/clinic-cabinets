import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, time, timedelta
import re
import numpy as np

import streamlit as st
import plotly

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
    'процедурный': 'Процедурные',
    'лаборатория': 'Лаборатория',
    'статистик': 'Администрация',
    'дневной стационар': 'Стационар',
    'физиотерапии': 'Физиотерапия',
    'перевязочная': 'Перевязочная',
    'биоматериал': 'Забор биоматериала',
    'квс': 'КВС',
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
    'Физиотерапия': '#2A9D8F',
    'Перевязочная': '#E9C46A',
    'Забор биоматериала': '#F4A261',
    'КВС': '#E76F51',
    'Прочее': '#BDC3C7',
    'Пусто': '#E8E8E8',
    'Нет данных': '#F5F5F5',
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


def get_display_name(full_name):
    if pd.isna(full_name):
        return ''
    s = str(full_name).strip()
    s_lower = s.lower()
    cabinet_keywords = [
        'кабинет', 'перевязочная', 'биоматериал', 'процедурн',
        'физиотерап', 'лаборатор', 'статистик', 'стационар', 'квс'
    ]
    if any(kw in s_lower for kw in cabinet_keywords):
        return s
    parts = s.split()
    return parts[0] if parts else s


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
    try:
        df = pd.read_excel(uploaded_file, sheet_name='Лист2', header=6)
    except Exception:
        df = pd.read_excel(uploaded_file, sheet_name=0, header=6)
    
    df.columns = ['Кабинет', 'Дата', 'Период', 'Доктор', 'Специализация']
    df = df.dropna(subset=['Дата', 'Период']).copy()

    def fix_cabinet(row):
        cab = row['Кабинет']
        if pd.isna(cab) or str(cab).strip() == '':
            return str(row['Доктор']).strip()
        try:
            return str(int(float(cab)))
        except:
            return str(cab).strip()

    df['Кабинет'] = df.apply(fix_cabinet, axis=1)
    df = df[df['Кабинет'].notna() & (df['Кабинет'] != '')].copy()

    df['date_parsed'] = pd.to_datetime(df['Дата'], format='%d.%m.%Y', errors='coerce')
    df = df.dropna(subset=['date_parsed'])
    df['date_str'] = df['date_parsed'].dt.strftime('%d.%m.%Y')
    df['date_short'] = df['date_parsed'].dt.strftime('%d.%m')

    def parse_period(p):
        m = re.match(r'(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})', str(p))
        if m:
            h1, m1, h2, m2 = map(int, m.groups())
            return time(h1, m1), time(h2, m2)
        return None, None

    df[['start_time', 'end_time']] = df['Период'].apply(
        lambda x: pd.Series(parse_period(x))
    )
    df['spec'] = df['Специализация'].apply(normalize_spec)
    df['surname'] = df['Доктор'].apply(get_display_name)

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


def add_legend(fig, colors, spec_to_code):
    for spec in sorted(spec_to_code.keys()):
        if spec in ('Пусто', 'Нет данных'):
            continue
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode='markers',
            marker=dict(size=14, color=colors.get(spec, '#999'),
                        line=dict(width=1, color='white')),
            name=spec,
            showlegend=True,
            hoverinfo='skip',
        ))


def create_overview_heatmap(df, selected_cabinets, selected_dates, colors, spec_to_code):
    df_f = df[df['Кабинет'].isin(selected_cabinets)].copy()

    all_dates = sorted(selected_dates,
                       key=lambda x: datetime.strptime(x + '.2026', '%d.%m.%Y'))
    all_cabs = sorted(selected_cabinets, key=cabinet_sort_key)

    if not df_f.empty:
        agg = df_f.groupby(['date_short', 'Кабинет']).agg({
            'spec': lambda x: x.mode().iloc[0] if not x.mode().empty else 'Прочее',
            'surname': lambda x: ', '.join(dict.fromkeys(x)),
            'hours': 'sum',
        }).reset_index()
    else:
        agg = pd.DataFrame(columns=['date_short', 'Кабинет', 'spec', 'surname', 'hours'])

    grid = pd.DataFrame([(d, c) for d in all_dates for c in all_cabs],
                        columns=['date_short', 'Кабинет'])
    grid = grid.merge(agg, on=['date_short', 'Кабинет'], how='left')

    dates_with_data = set(df_f['date_short'].unique()) if not df_f.empty else set()

    def get_cell_info(row):
        if pd.isna(row['spec']):
            if row['date_short'] in dates_with_data:
                return 'Пусто', 'Пусто', 0.0
            else:
                return 'Нет данных', 'Нет данных', 0.0
        return row['spec'], row['surname'], row['hours']

    grid[['spec', 'surname', 'hours']] = grid.apply(
        lambda r: pd.Series(get_cell_info(r)), axis=1
    )

    grid['code'] = grid['spec'].map(lambda s: spec_to_code.get(s, spec_to_code['Нет данных']))

    pivot_code = grid.pivot(index='Кабинет', columns='date_short', values='code')
    pivot_code = pivot_code.reindex(index=all_cabs, columns=all_dates)
    pivot_code = pivot_code.fillna(spec_to_code['Нет данных'])

    pivot_spec = grid.pivot(index='Кабинет', columns='date_short', values='spec')
    pivot_spec = pivot_spec.reindex(index=all_cabs, columns=all_dates).fillna('Нет данных')
    pivot_docs = grid.pivot(index='Кабинет', columns='date_short', values='surname')
    pivot_docs = pivot_docs.reindex(index=all_cabs, columns=all_dates).fillna('Нет данных')
    pivot_hours = grid.pivot(index='Кабинет', columns='date_short', values='hours')
    pivot_hours = pivot_hours.reindex(index=all_cabs, columns=all_dates).fillna(0.0)

    # 2D-массив hover-текстов (строки × столбцы)
    hover_text = np.empty((len(all_cabs), len(all_dates)), dtype=object)
    for i, cab in enumerate(all_cabs):
        for j, d in enumerate(all_dates):
            spec = pivot_spec.iloc[i, j]
            docs = pivot_docs.iloc[i, j]
            hrs = pivot_hours.iloc[i, j]
            if spec == 'Нет данных':
                hover_text[i, j] = f"Кабинет: {cab}\nДата: {d}\nНет данных"
            elif spec == 'Пусто':
                hover_text[i, j] = f"Кабинет: {cab}\nДата: {d}\nПусто"
            else:
                hover_text[i, j] = (
                    f"Кабинет: {cab}\n"
                    f"Дата: {d}\n"
                    f"Специализация: {spec}\n"
                    f"Врач(и): {docs}\n"
                    f"Часов: {hrs:.1f}"
                )

    n = len(spec_to_code)
    colorscale = []
    for spec, code in sorted(spec_to_code.items(), key=lambda x: x[1]):
        pos = code / max(n - 1, 1)
        colorscale.append([pos, colors[spec]])

    fig = go.Figure(data=go.Heatmap(
        z=pivot_code.values,
        x=all_dates,
        y=all_cabs,
        hovertext=hover_text,
        hoverinfo='text',
        colorscale=colorscale,
        showscale=False,
        zmin=0,
        zmax=n - 1,
        xgap=0,
        ygap=0,
    ))

    add_legend(fig, colors, spec_to_code)

    fig.update_layout(
        title='📅 Обзорная тепловая карта (цвет = специализация)',
        xaxis_title='Дата',
        yaxis_title='Кабинет',
        height=max(500, len(all_cabs) * 48),
        width=max(900, len(all_dates) * 100),
        yaxis=dict(
            categoryorder='array',
            categoryarray=all_cabs,
            autorange='reversed',
            dtick=1,
            showgrid=True,
            gridcolor='#E0E0E0',
            gridwidth=1,
        ),
        xaxis=dict(
            dtick=1,
            showgrid=True,
            gridcolor='#E0E0E0',
            gridwidth=1,
            type='category',
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(size=12),
        margin=dict(l=80, r=40, t=80, b=60),
        hovermode='closest',
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=-0.25,
            xanchor='center',
            x=0.5,
            font=dict(size=10),
            itemsizing='constant',
        ),
    )
    return fig


def create_hourly_heatmap(df, selected_date, selected_cabinets, colors, spec_to_code):
    df_day = df[(df['date_str'] == selected_date) &
                df['Кабинет'].isin(selected_cabinets)].copy()

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
    hover_text = []

    for cab in all_cabs:
        cab_df = df_day[df_day['Кабинет'] == cab]
        z_row, hover_row = [], []
        for h in hours:
            docs = []
            specs = []
            for _, r in cab_df.iterrows():
                if is_working(r, h):
                    docs.append(r['surname'])
                    specs.append(r['spec'])
            if docs:
                unique_docs = list(dict.fromkeys(docs))
                txt = ', '.join(unique_docs)
                spec_val = specs[0]
                z_row.append(spec_to_code.get(spec_val, spec_to_code['Пусто']))
                hover_row.append(
                    f"Кабинет: {cab}\n"
                    f"Время: {h}\n"
                    f"Специализация: {spec_val}\n"
                    f"Врач: {txt}"
                )
            else:
                z_row.append(spec_to_code['Пусто'])
                hover_row.append(f"Кабинет: {cab}\nВремя: {h}\nПусто")
        z_matrix.append(z_row)
        hover_text.append(hover_row)

    fig = go.Figure(data=go.Heatmap(
        z=z_matrix,
        x=hours,
        y=all_cabs,
        hovertext=np.array(hover_text, dtype=object),
        hoverinfo='text',
        colorscale=colorscale,
        showscale=False,
        zmin=0,
        zmax=n - 1,
        xgap=1,
        ygap=2,
    ))

    add_legend(fig, colors, spec_to_code)

    fig.update_layout(
        title=f'⏰ Почасовая карта — {selected_date}',
        xaxis_title='Время',
        yaxis_title='Кабинет',
        height=max(520, len(all_cabs) * 48),
        width=1450,
        yaxis=dict(
            categoryorder='array',
            categoryarray=all_cabs,
            autorange='reversed',
            dtick=1,
            showgrid=True,
            gridcolor='#E0E0E0',
            gridwidth=1,
        ),
        xaxis=dict(
            dtick=1,
            showgrid=True,
            gridcolor='#E0E0E0',
            gridwidth=1,
            tickangle=45,
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(size=12),
        margin=dict(l=80, r=40, t=80, b=100),
        hovermode='closest',
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=-0.3,
            xanchor='center',
            x=0.5,
            font=dict(size=10),
            itemsizing='constant',
        ),
    )
    return fig


# ==================== ПРИЛОЖЕНИЕ ====================
def main():
    st.markdown("# 🏥 Тепловая карта загрузки кабинетов")
    st.markdown(
        "<p style='color:#666; font-size:1.05rem;'>"
        "Цвет ячейки = <b>специализация</b> &nbsp;|&nbsp; "
        "Наведите на ячейку для подробной информации &nbsp;|&nbsp; "
        "Серый = <b>Пусто</b> &nbsp;|&nbsp; "
        "Белый = <b>Нет данных</b>"
        "</p>",
        unsafe_allow_html=True,
    )

    uploaded_file = st.file_uploader(
        "📁 Загрузите отчёт Excel (cabinets.xlsx)", type=['xlsx', 'xls']
    )

    if uploaded_file is None:
        st.info("👆 Загрузите файл с отчётом о загрузке кабинетов.")
        st.markdown("""
        **Ожидаемый формат (начиная с 7-й строки, Лист2):**
        | Кабинет | Дата | Период | Доктор | Специализация |
        """)
        return

    with st.spinner('⏳ Читаем и обрабатываем данные…'):
        df = parse_excel_new(uploaded_file)

    if df.empty:
        st.error("❌ Не удалось распознать данные. Проверьте формат файла.")
        return

    # Фиксированный список кабинетов: 1-25 + остальные из данных
    numeric_cabinets = [str(i) for i in range(1, 26)]
    other_cabinets = [
        str(c) for c in df['Кабинет'].unique()
        if str(c) not in numeric_cabinets
    ]
    all_cabinets = numeric_cabinets + sorted(other_cabinets, key=cabinet_sort_key)
    selected_cabinets = all_cabinets

    # Цвета
    all_specs = sorted(df['spec'].unique())
    if 'Пусто' not in all_specs:
        all_specs = ['Пусто'] + all_specs
    if 'Нет данных' not in all_specs:
        all_specs = ['Нет данных'] + all_specs
    colors = assign_colors(all_specs)
    spec_to_code = {
        s: i for i, s in enumerate(
            sorted(all_specs, key=lambda x: list(colors.keys()).index(x) if x in colors else 999)
        )
    }

    # Метрики
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("👨‍⚕️ Врачей/записей", df['Доктор'].nunique())
    with c2:
        st.metric("🚪 Кабинетов", len(selected_cabinets))
    with c3:
        st.metric("📅 Дней в отчёте", df['date_short'].nunique())
    with c4:
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

        st.markdown(f"**🚪 Кабинеты:** 1–25 + специальные ({len(selected_cabinets)} всего)")

        all_dates_full = sorted(
            df['date_str'].unique(),
            key=lambda x: datetime.strptime(x, '%d.%m.%Y')
        )
        all_dates_short = sorted(
            df['date_short'].unique(),
            key=lambda x: datetime.strptime(x + '.2026', '%d.%m.%Y')
        )

        if mode == "📅 Обзор по дням":
            date_opt = st.radio(
                "Диапазон:",
                ["Последние 7 дней", "Последние 30 дней", "Все дни", "Выбрать диапазон"],
                index=0,
            )
            if date_opt == "Все дни":
                selected_dates = all_dates_short
                date_range_label = f"{selected_dates[0]} – {selected_dates[-1]}"
            elif date_opt == "Последние 7 дней":
                selected_dates = (all_dates_short[-7:]
                                  if len(all_dates_short) >= 7
                                  else all_dates_short)
                date_range_label = f"{selected_dates[0]} – {selected_dates[-1]}"
            elif date_opt == "Последние 30 дней":
                selected_dates = (all_dates_short[-30:]
                                  if len(all_dates_short) >= 30
                                  else all_dates_short)
                date_range_label = f"{selected_dates[0]} – {selected_dates[-1]}"
            else:
                if len(all_dates_full) > 0:
                    min_date = datetime.strptime(all_dates_full[0], '%d.%m.%Y')
                    max_date = datetime.strptime(all_dates_full[-1], '%d.%m.%Y')
                else:
                    min_date = datetime.now()
                    max_date = datetime.now()

                date_range = st.date_input(
                    "Выберите диапазон:",
                    value=(min_date, max_date),
                    min_value=min_date - timedelta(days=365),
                    max_value=max_date + timedelta(days=365),
                )
                if len(date_range) == 2:
                    start, end = date_range
                    date_list = []
                    current = start
                    while current <= end:
                        date_list.append(current.strftime('%d.%m'))
                        current += timedelta(days=1)
                    selected_dates = date_list
                    date_range_label = f"{selected_dates[0]} – {selected_dates[-1]}"
                else:
                    selected_dates = all_dates_short[-7:]
                    date_range_label = f"{selected_dates[0]} – {selected_dates[-1]}"
            selected_date = None
        else:
            selected_date = st.selectbox("Дата:", all_dates_full)
            selected_dates = []
            date_range_label = selected_date

        st.divider()
        st.markdown("**🩺 Специализации:**")
        for spec in sorted(spec_to_code.keys()):
            if spec in ('Пусто', 'Нет данных'):
                continue
            color = colors.get(spec, '#999')
            st.markdown(
                f"<span style='display:inline-block; width:12px; height:12px; "
                f"background:{color}; border-radius:2px; margin-right:6px;'>"
                f"</span>{spec}",
                unsafe_allow_html=True,
            )
        st.markdown(
            f"<span style='display:inline-block; width:12px; height:12px; "
            f"background:{colors['Пусто']}; border-radius:2px; margin-right:6px;'>"
            f"</span>Пусто",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<span style='display:inline-block; width:12px; height:12px; "
            f"background:{colors['Нет данных']}; border-radius:2px; margin-right:6px;'>"
            f"</span>Нет данных",
            unsafe_allow_html=True,
        )

    # ===== ОСНОВНАЯ ОБЛАСТЬ =====
    if mode == "📅 Обзор по дням":
        st.subheader(
            f"📅 Обзор с {date_range_label} "
            f"({len(selected_dates)} дн.)"
        )
        fig = create_overview_heatmap(
            df, selected_cabinets, selected_dates, colors, spec_to_code
        )
        st.plotly_chart(
    fig,
    use_container_width=False,
    config={
        "displayModeBar": False,
        "scrollZoom": False
    }
)

        with st.expander("📊 Таблица данных"):
            show = df[
                df['Кабинет'].isin(selected_cabinets) &
                df['date_short'].isin([d for d in selected_dates if d in df['date_short'].values])
            ][['date_str', 'Кабинет', 'Доктор', 'spec', 'Период', 'hours']]
            show = show.sort_values(['date_str', 'Кабинет', 'Период'])
            st.dataframe(show, use_container_width=True, hide_index=True)
    else:
        st.subheader(f"⏰ Почасовая карта — {selected_date}")
        fig = create_hourly_heatmap(
            df, selected_date, selected_cabinets, colors, spec_to_code
        )
        st.plotly_chart(
    fig,
    use_container_width=False,
    config={
        "displayModeBar": False,
        "scrollZoom": False
    }
)

        df_day = df[df['date_str'] == selected_date]
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Работающих врачей/записей", df_day['Доктор'].nunique())
        with c2:
            st.metric("Занятых кабинетов", df_day['Кабинет'].nunique())
        with c3:
            st.metric("Всего часов", round(df_day['hours'].sum(), 1))

        with st.expander("📊 Таблица данных за день"):
            show = df_day[df_day['Кабинет'].isin(selected_cabinets)][
                ['Кабинет', 'Доктор', 'spec', 'Период', 'hours']
            ].sort_values(['Кабинет', 'Период'])
            st.dataframe(show, use_container_width=True, hide_index=True)

st.divider()
st.write("### Тест hover")

test_fig = go.Figure(
    go.Scatter(
        x=[1, 2, 3],
        y=[1, 2, 3],
        mode="markers",
        marker=dict(size=30),
        hovertemplate="Работает! x=%{x}<extra></extra>"
    )
)

st.plotly_chart(test_fig)

if __name__ == "__main__":
    main()
