import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, time, timedelta
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
            'Период': lambda x: '; '.join(dict.fromkeys(x)),
        }).reset_index()
    else:
        agg = pd.DataFrame(columns=['date_short', 'Кабинет', 'spec', 'surname', 'hours', 'Период'])

    grid = pd.DataFrame([(d, c) for d in all_dates for c in all_cabs],
                        columns=['date_short', 'Кабинет'])
    grid = grid.merge(agg, on=['date_short', 'Кабинет'], how='left')
    grid['Период'] = grid['Период'].fillna('-')

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

    x_list, y_list, c_list, h_list = [], [], [], []
    for _, row in grid.iterrows():
        x_list.append(row['date_short'])
        y_list.append(row['Кабинет'])
        spec = row['spec']
        c_list.append(colors.get(spec, '#999'))
        if spec == 'Нет данных':
            h_list.append(f"<b>Кабинет:</b> {row['Кабинет']}<br><b>Дата:</b> {row['date_short']}<br>Нет данных")
        elif spec == 'Пусто':
            h_list.append(f"<b>Кабинет:</b> {row['Кабинет']}<br><b>Дата:</b> {row['date_short']}<br>Пусто")
        else:
            h_list.append(
                f"<b>Кабинет:</b> {row['Кабинет']}<br>"
                f"<b>Дата:</b> {row['date_short']}<br>"
                f"<b>Время:</b> {row['Период']}<br>"
                f"<b>Специализация:</b> {spec}<br>"
                f"<b>Врач(и):</b> {row['surname']}<br>"
                f"<b>Часов:</b> {row['hours']:.1f}"
            )

    width = max(900, len(all_dates) * 90)
    height = max(500, len(all_cabs) * 50)
    plot_w = width - 120
    plot_h = height - 140
    marker_size = min(plot_w / len(all_dates), plot_h / len(all_cabs)) * 0.92

    fig = go.Figure(data=go.Scatter(
        x=x_list,
        y=y_list,
        mode='markers',
        marker=dict(
            symbol='square',
            size=marker_size,
            color=c_list,
            line=dict(width=0),
        ),
        hovertext=h_list,
        hoverinfo='text',
        showlegend=False,
    ))

    fig.update_layout(
        title='📅 Обзорная тепловая карта (цвет = специализация)',
        xaxis_title='Дата',
        yaxis_title='Кабинет',
        height=height,
        width=width,
        yaxis=dict(
            type='category',
            categoryorder='array',
            categoryarray=all_cabs,
            autorange='reversed',
            dtick=1,
            showgrid=True,
            gridcolor='#E0E0E0',
            gridwidth=1,
        ),
        xaxis=dict(
            categoryorder='array',
            categoryarray=all_dates,
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
        showlegend=False,
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

    x_list, y_list, c_list, h_list = [], [], [], []
    for cab in all_cabs:
        cab_df = df_day[df_day['Кабинет'] == cab]
        for h in hours:
            docs = []
            specs = []
            for _, r in cab_df.iterrows():
                if is_working(r, h):
                    docs.append(r['surname'])
                    specs.append(r['spec'])
            x_list.append(h)
            y_list.append(cab)
            if docs:
                unique_docs = list(dict.fromkeys(docs))
                txt = ', '.join(unique_docs)
                spec_val = specs[0]
                c_list.append(colors.get(spec_val, '#999'))
                h_list.append(
                    f"<b>Кабинет:</b> {cab}<br>"
                    f"<b>Время:</b> {h}<br>"
                    f"<b>Специализация:</b> {spec_val}<br>"
                    f"<b>Врач:</b> {txt}"
                )
            else:
                c_list.append(colors.get('Пусто', '#999'))
                h_list.append(f"<b>Кабинет:</b> {cab}<br><b>Время:</b> {h}<br>Пусто")

    width = 1450
    height = max(600, len(all_cabs) * 50)
    plot_w = width - 120
    plot_h = height - 180
    marker_size = min(plot_w / len(hours), plot_h / len(all_cabs)) * 0.88

    fig = go.Figure(data=go.Scatter(
        x=x_list,
        y=y_list,
        mode='markers',
        marker=dict(
            symbol='square',
            size=marker_size,
            color=c_list,
            line=dict(width=0.5, color='#CCCCCC'),
        ),
        hovertext=h_list,
        hoverinfo='text',
        showlegend=False,
    ))

    fig.update_layout(
        title=f'⏰ Почасовая карта — {selected_date}',
        xaxis_title='Время',
        yaxis_title='Кабинет',
        height=height,
        width=width,
        yaxis=dict(
            type='category',
            categoryorder='array',
            categoryarray=all_cabs,
            autorange='reversed',
            dtick=1,
            showgrid=True,
            gridcolor='#E0E0E0',
            gridwidth=1,
        ),
        xaxis=dict(
            categoryorder='array',
            categoryarray=hours,
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
        showlegend=False,
    )
    return fig


# ==================== НОВАЯ ФУНКЦИЯ: СПЕЦИАЛЬНЫЕ КАБИНЕТЫ ====================
def create_special_hourly_heatmap(df, selected_date, colors):
    """Почасовая карта для специальных (безномерных) кабинетов."""
    special_cabs = [
        "Кабинет забора мазков",
        "Кабинет повторных приемов",
        "Травмпункт Перевязочная Северная",
        "Кабинет описания ЭКГ .",
        "Кабинет описания Холтеров и СМАДов",
        "Кабинет описания спирографии",
    ]
    special_spec_map = {
        "Кабинет забора мазков": "Процедурные",
        "Кабинет повторных приемов": "Процедурные",
        "Травмпункт Перевязочная Северная": "Травматология",
        "Кабинет описания ЭКГ .": "Процедурные",
        "Кабинет описания Холтеров и СМАДов": "Процедурные",
        "Кабинет описания спирографии": "Процедурные",
    }

    df_day = df[(df['date_str'] == selected_date) &
                df['Кабинет'].isin(special_cabs)].copy()

    hours = [f"{h:02d}:{m:02d}" for h in range(7, 24) for m in (0, 30)]

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

    x_list, y_list, c_list, h_list = [], [], [], []
    for cab in special_cabs:
        cab_df = df_day[df_day['Кабинет'] == cab]
        for hr in hours:
            docs = []
            specs = []
            for _, r in cab_df.iterrows():
                if is_working(r, hr):
                    docs.append(r['surname'])
                    specs.append(r['spec'])
            x_list.append(hr)
            y_list.append(cab)
            if docs:
                unique_docs = list(dict.fromkeys(docs))
                txt = ', '.join(unique_docs)
                spec_val = specs[0] if specs else special_spec_map[cab]
                c_list.append(colors.get(spec_val, '#999'))
                h_list.append(
                    f"<b>Кабинет:</b> {cab}<br>"
                    f"<b>Время:</b> {hr}<br>"
                    f"<b>Специализация:</b> {spec_val}<br>"
                    f"<b>Врач:</b> {txt}"
                )
            else:
                spec_val = special_spec_map[cab]
                c_list.append(colors.get(spec_val, '#999'))
                h_list.append(
                    f"<b>Кабинет:</b> {cab}<br>"
                    f"<b>Время:</b> {hr}<br>"
                    f"<b>Специализация:</b> {spec_val}<br>"
                    f"Пусто"
                )

    width = 1450
    height = max(400, len(special_cabs) * 65)
    plot_w = width - 120
    plot_h = height - 180
    marker_size = min(plot_w / len(hours), plot_h / len(special_cabs)) * 0.88

    fig = go.Figure(data=go.Scatter(
        x=x_list,
        y=y_list,
        mode='markers',
        marker=dict(
            symbol='square',
            size=marker_size,
            color=c_list,
            line=dict(width=0.5, color='#CCCCCC'),
        ),
        hovertext=h_list,
        hoverinfo='text',
        showlegend=False,
    ))

    fig.update_layout(
        title=f'🏥 Специальные кабинеты — {selected_date}',
        xaxis_title='Время',
        yaxis_title='Кабинет',
        height=height,
        width=width,
        yaxis=dict(
            type='category',
            categoryorder='array',
            categoryarray=special_cabs,
            dtick=1,
            showgrid=True,
            gridcolor='#E0E0E0',
            gridwidth=1,
        ),
        xaxis=dict(
            categoryorder='array',
            categoryarray=hours,
            dtick=1,
            showgrid=True,
            gridcolor='#E0E0E0',
            gridwidth=1,
            tickangle=45,
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(size=12),
        margin=dict(l=300, r=40, t=80, b=100),  # увеличен левый отступ для длинных названий
        showlegend=False,
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

    # Только кабинеты 1–25
    selected_cabinets = [str(i) for i in range(1, 26)]

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

    with st.sidebar:
        st.header("⚙️ Фильтры")

        # Детально по часам — первый и по умолчанию
        mode = st.radio(
            "Режим:",
            ["⏰ Детально по часам", "📅 Обзор по дням"],
            index=0,
        )

        st.markdown("**🚪 Кабинеты:** 1–25")

        all_dates_full = sorted(
            df['date_str'].unique(),
            key=lambda x: datetime.strptime(x, '%d.%m.%Y')
        )
        all_dates_short = sorted(
            df['date_short'].unique(),
            key=lambda x: datetime.strptime(x + '.2026', '%d.%m.%Y')
        )

        if mode == "📅 Обзор по дням":
            st.caption("💡 Для корректного отображения выбирайте диапазон до 40 дней")
            
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
            if spec in ('Пусто', 'Нет данных', 'Администрация'):
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
            f"background:{colors.get('Пусто', '#999')}; border-radius:2px; margin-right:6px;'>"
            f"</span>Пусто",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<span style='display:inline-block; width:12px; height:12px; "
            f"background:{colors.get('Нет данных', '#999')}; border-radius:2px; margin-right:6px;'>"
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
        st.plotly_chart(fig, use_container_width=False)

        with st.expander("📊 Таблица данных"):
            show = df[
                df['Кабинет'].isin(selected_cabinets) &
                df['date_short'].isin([d for d in selected_dates if d in df['date_short'].values])
            ][['date_str', 'Кабинет', 'Доктор', 'spec', 'Период', 'hours']]
            show = show.sort_values(['date_str', 'Кабинет', 'Период'])
            st.dataframe(show, use_container_width=True, hide_index=True)

        # --- СПЕЦИАЛЬНЫЕ КАБИНЕТЫ (последняя дата диапазона) ---
        st.divider()
        st.subheader("🏥 Специальные кабинеты")
        last_short = selected_dates[-1] if selected_dates else None
        if last_short:
            matching = df[df['date_short'] == last_short]['date_str'].unique()
            special_date = matching[0] if len(matching) > 0 else None
        else:
            special_date = None
        
        if special_date:
            fig_special = create_special_hourly_heatmap(df, special_date, colors)
            st.plotly_chart(fig_special, use_container_width=False)

    else:
        st.subheader(f"⏰ Почасовая карта — {selected_date}")
        fig = create_hourly_heatmap(
            df, selected_date, selected_cabinets, colors, spec_to_code
        )
        st.plotly_chart(fig, use_container_width=False)

        with st.expander("📊 Таблица данных за день"):
            df_day = df[df['date_str'] == selected_date]
            show = df_day[df_day['Кабинет'].isin(selected_cabinets)][
                ['Кабинет', 'Доктор', 'spec', 'Период', 'hours']
            ].sort_values(['Кабинет', 'Период'])
            st.dataframe(show, use_container_width=True, hide_index=True)

        # --- СПЕЦИАЛЬНЫЕ КАБИНЕТЫ (та же выбранная дата) ---
        st.divider()
        st.subheader("🏥 Специальные кабинеты")
        fig_special = create_special_hourly_heatmap(df, selected_date, colors)
        st.plotly_chart(fig_special, use_container_width=False)


if __name__ == "__main__":
    main()
