import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, time, timedelta
import re
import io

st.set_page_config(page_title="График загрузки кабинетов", layout="wide")

# ==================== ЕДИНЫЙ СТИЛЬ ====================
CELL_SIZE = 46
MARKER_SIZE = 42
BORDER_WIDTH = 1.5
BORDER_COLOR = '#444444'

# ==================== НОРМАЛИЗАЦИЯ ====================
SPEC_MAP = {
    'терапевт': 'Терапия',
    'гастроэнтеролог, терапевт': 'Терапия',
    'отоларинголог, терапевт': 'Терапия',
    'кардиолог': 'Кардиология',
    'кардиолог-невролог': 'Кардиология',
    'эндокринолог': 'Эндокринология',
    'акушер-гинеколог, эндокринолог': 'Эндокринология',
    'невролог': 'Неврология',
    'хирургия': 'Хирургия',
    'хирург': 'Хирургия',
    'сосудистый хирург': 'Хирургия',
    'колопроктолог, хирург': 'Хирургия',
    'травматолог-ортопед, хирург': 'Хирургия',
    'травматолог': 'Травматология',
    'ортопед': 'Травматология',
    'травматолог-ортопед': 'Травматология',
    'рентгенолог': 'Рентген',
    'рентген': 'Рентген',
    'ультразвуковой': 'УЗИ',
    'уздг': 'УЗИ',
    'врач ультразвуковой диагностики': 'УЗИ',
    'акушер-гинеколог, узд': 'УЗИ',
    'функциональной диагностики': 'Функц. диагностика',
    'врач функциональной диагностики': 'Функц. диагностика',
    'гинеколог': 'Гинекология',
    'акушер': 'Гинекология',
    'акушер-гинеколог': 'Гинекология',
    'уролог': 'Урология',
    'дерматовенеролог': 'Дерматология',
    'дерматолог': 'Дерматология',
    'онколог': 'Онкология',
    'онколог-маммолог': 'Онкология',
    'маммолог': 'Онкология',
    'флеболог': 'Флебология',
    'гастроэнтеролог': 'Гастроэнтерология',
    'отоларинголог': 'ЛОР',
    'колопроктолог': 'Колопроктология',
    'психолог': 'Психология',
    'психиатр': 'Психиатрия',
    'психотерапевт': 'Психиатрия',
    'аллерголог-иммунолог': 'Аллергология-иммунология',
    'аллерголог': 'Аллергология-иммунология',
    'иммунолог': 'Аллергология-иммунология',
    'пульмонолог': 'Пульмонология',
    'пульмонолог-фтизиатр': 'Пульмонология',
    'фтизиатр': 'Пульмонология',
    'мануальный терапевт': 'Мануальная терапия',
    'мануальная': 'Мануальная терапия',
    'процедурные кабинеты': 'Процедурные',
    'процедурный': 'Процедурные',
    'кабинет (кво)': 'Процедурные',
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
    'Психиатрия': '#8d99ae',
    'Аллергология-иммунология': '#264653',
    'Пульмонология': '#8ac926',
    'Мануальная терапия': '#ffca3a',
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
    '#2a9d8f', '#e9c46a', '#f4a261', '#e76f51',
    '#1982c4', '#ff595e', '#d62828', '#f77f00',
    '#fcbf49', '#eae2b7', '#003049',
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
    """Фамилия для текста внутри клетки (коротко)."""
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


def get_initials(full_name):
    """Фамилия И. О. для подсказок (hover)."""
    if pd.isna(full_name):
        return ''
    s = str(full_name).strip()
    if not s:
        return ''
    s_lower = s.lower()
    cabinet_keywords = [
        'кабинет', 'перевязочная', 'биоматериал', 'процедурн',
        'физиотерап', 'лаборатор', 'статистик', 'стационар', 'квс',
        'операционная', 'хирургия', 'рентген'
    ]
    if any(kw in s_lower for kw in cabinet_keywords):
        return s
    parts = s.split()
    if len(parts) >= 3:
        fam, name, otch = parts[0], parts[1], parts[2]
        name = name.replace('.', '')
        otch = otch.replace('.', '')
        return f"{fam} {name[0]}. {otch[0]}."
    elif len(parts) == 2:
        fam, name = parts[0], parts[1]
        name = name.replace('.', '')
        if len(name) == 1:
            return f"{fam} {name}."
        return f"{fam} {name[0]}."
    else:
        return s


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


# ==================== НОРМАЛИЗАЦИЯ КАБИНЕТОВ ====================
def normalize_cabinet(raw):
    if pd.isna(raw):
        return None

    s = str(raw).strip()

    if not s:
        return None

    # Excel может отдавать номер кабинета как "12.0"
    if re.match(r'^\d+\.0$', s):
        return str(int(float(s)))

    # Форматы вроде 12.01 / 12-01
    m = re.search(r'(\d+)[-\.](\d+)$', s)

    if m:
        left, right = m.group(1), m.group(2)

        if len(right) == 2 and len(left) <= 2:
            return f"{left}{right}"

    # Обычное числовое значение
    try:
        val = float(s)

        if val == int(val):
            return str(int(val))

        return str(val)

    except (ValueError, TypeError):
        pass

    return s


def cabinet_sort_key(c):
    s = str(c)
    parts = s.split('.')
    if len(parts) == 2:
        left, right = parts[0], parts[1]
        if left.isdigit() and right.isdigit():
            left_int = int(left)
            if left_int >= 100:
                return (0, left_int, int(right))
            else:
                return (1, left_int, int(right))
    if s.isdigit():
        num = int(s)
        if num >= 100:
            return (0, num, 0)
        else:
            return (1, num, 0)
    return (2, s, 0)


# ==================== ИЗВЛЕЧЕНИЕ НАЗВАНИЯ КЛИНИКИ ====================
def clean_clinic_name(name):
    if pd.isna(name):
        return ''
    name = str(name).strip()
    name = re.sub(r'^\\d{2,}\\s*[-–—.]?\\s*', '', name)
    name = re.sub(r'\\s*[-–—.]?\\s*\\d{2,}$', '', name)
    forms = [
        'ООО', 'ОАО', 'ЗАО', 'АО', 'ИП', 'ПАО', 'НАО',
        'ФГБУ', 'ФГАОУ', 'ФГБОУ', 'ФГАУ', 'МБУ', 'ГБУ',
        'ГБУЗ', 'МБУЗ', 'ФМБА', 'МИНЗДРАВ'
    ]
    for form in forms:
        name = re.sub(rf'\\b{re.escape(form)}\\b', '', name, flags=re.IGNORECASE)
    name = re.sub(r'^[.,;:\\-\\s]+', '', name)
    name = re.sub(r'[.,;:\\-\\s]+$', '', name)
    name = re.sub(r'\\s+', ' ', name).strip()
    return name


def extract_clinic_name(file_bytes):
    try:
        df_raw = pd.read_excel(io.BytesIO(file_bytes), sheet_name='Лист2', header=None, nrows=15)
    except Exception:
        try:
            df_raw = pd.read_excel(io.BytesIO(file_bytes), sheet_name=0, header=None, nrows=15)
        except Exception:
            return ''
    candidates = []
    for col in df_raw.columns:
        for val in df_raw[col].dropna():
            s = str(val).strip()
            if len(s) >= 5 and not s.lower().startswith('http') and not s.replace('.', '').replace(',', '').isdigit():
                candidates.append(s)
    if not candidates:
        return ''
    raw_name = max(candidates, key=len)
    return clean_clinic_name(raw_name)


# ==================== ПАРСИНГ ====================
@st.cache_data(show_spinner=False)
def parse_excel_new(file_bytes):
    """Читает Excel, автоматически находя начало данных."""
    try:
        preview = pd.read_excel(io.BytesIO(file_bytes), sheet_name='Лист2', header=None, nrows=20)
    except Exception:
        preview = pd.read_excel(io.BytesIO(file_bytes), sheet_name=0, header=None, nrows=20)

    skiprows = 4
    for idx, row in preview.iterrows():
        row_str = ' '.join(str(v).lower() if pd.notna(v) else '' for v in row)
        if 'кабинет' in row_str and ('дата' in row_str or 'период' in row_str or 'доктор' in row_str):
            skiprows = idx + 1
            break

    try:
        df = pd.read_excel(io.BytesIO(file_bytes), sheet_name='Лист2', header=None, skiprows=skiprows)
    except Exception:
        df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=0, header=None, skiprows=skiprows)

    if df.shape[1] < 5:
        return pd.DataFrame()

    df = df.iloc[:, :5].copy()
    df.columns = ['Кабинет', 'Дата', 'Период', 'Доктор', 'Специализация']

    df = df.dropna(subset=['Дата', 'Период']).copy()

    df['Кабинет'] = df['Кабинет'].apply(normalize_cabinet)
    df = df.dropna(subset=['Кабинет'])
    df = df[df['Кабинет'] != ''].copy()

    df['date_parsed'] = pd.to_datetime(df['Дата'], format='%d.%m.%Y', errors='coerce')
    if df['date_parsed'].isna().all():
        df['date_parsed'] = pd.to_datetime(df['Дата'], errors='coerce')
    df = df.dropna(subset=['date_parsed'])
    df['date_str'] = df['date_parsed'].dt.strftime('%d.%m.%Y')
    df['date_short'] = df['date_parsed'].dt.strftime('%d.%m')

    def parse_period(p):
        if pd.isna(p):
            return None, None

        s = str(p).strip()
        s = s.replace('–', '-').replace('—', '-')

        m = re.match(
            r'^\s*(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})\s*$',
            s
        )

        if not m:
            return None, None

        h1, m1, h2, m2 = map(int, m.groups())

        return time(h1, m1), time(h2, m2)

    df[['start_time', 'end_time']] = df['Период'].apply(
        lambda x: pd.Series(parse_period(x))
    )
    df['spec'] = df['Специализация'].apply(normalize_spec)
    df['surname'] = df['Доктор'].apply(get_display_name)
    df['doctor_initials'] = df['Доктор'].apply(get_initials)

    def time_to_min(t):
        return t.hour * 60 + t.minute if pd.notna(t) else None

    df['hours'] = 0.0
    mask = df['start_time'].notna() & df['end_time'].notna()
    if mask.any():
        start_min = df.loc[mask, 'start_time'].map(time_to_min)
        end_min = df.loc[mask, 'end_time'].map(time_to_min)
        df.loc[mask, 'hours'] = ((end_min - start_min) / 60).clip(lower=0)

    return df


# ==================== ВИЗУАЛИЗАЦИИ ====================

def hex_to_rgba(hex_color, alpha):
    """Преобразует #RRGGBB в rgba(R,G,B,alpha)."""
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f'rgba({r},{g},{b},{alpha})'


def create_overview_heatmap(df, selected_cabinets, selected_dates, colors):
    # ИСКЛЮЧАЕМ перевязочную из обзорного графика
    df_f = df[
        df['Кабинет'].isin(selected_cabinets) &
        ~df['surname'].str.lower().str.contains('перевязочная', na=False)
    ].copy()

    all_dates = sorted(selected_dates,
                       key=lambda x: datetime.strptime(x + '.2026', '%d.%m.%Y'))
    all_cabs = sorted(selected_cabinets, key=cabinet_sort_key)

    # Словари для быстрого доступа к индексам
    date_to_idx = {d: i for i, d in enumerate(all_dates)}
    cab_to_idx = {c: i for i, c in enumerate(all_cabs)}

    # Группировка данных по ячейкам
    cell_records = {}
    for _, row in df_f.iterrows():
        key = (row['date_short'], row['Кабинет'])
        cell_records.setdefault(key, []).append(row)

    dates_with_data = set(df_f['date_short'].unique()) if not df_f.empty else set()

    shapes = []
    hover_x, hover_y, hover_text = [], [], []

    EMPTY_COLOR = colors.get('Пусто', '#E8E8E8')
    NO_DATA_COLOR = colors.get('Нет данных', '#F5F5F5')
    MAX_HOURS = 12.0

    for date_short in all_dates:
        for cab in all_cabs:
            i_date = date_to_idx[date_short]
            i_cab = cab_to_idx[cab]

            # Границы ячейки в координатах категорий
            x0 = i_date - 0.5
            x1 = i_date + 0.5
            y0_cell = i_cab - 0.5
            y1_cell = i_cab + 0.5

            key = (date_short, cab)
            records = cell_records.get(key, [])

            if not records:
                if date_short in dates_with_data:
                    # Пусто в день, где есть данные по другим кабинетам
                    shapes.append(dict(
                        type='rect',
                        x0=x0, x1=x1, y0=y0_cell, y1=y1_cell,
                        fillcolor=EMPTY_COLOR,
                        line=dict(width=BORDER_WIDTH, color=BORDER_COLOR),
                        layer='above'
                    ))
                    hover_text.append(
                        f"<b>Кабинет:</b> {cab}<br><b>Дата:</b> {date_short}<br>Пусто"
                    )
                else:
                    # Нет данных вообще
                    shapes.append(dict(
                        type='rect',
                        x0=x0, x1=x1, y0=y0_cell, y1=y1_cell,
                        fillcolor=NO_DATA_COLOR,
                        line=dict(width=BORDER_WIDTH, color=BORDER_COLOR),
                        layer='above'
                    ))
                    hover_text.append(
                        f"<b>Кабинет:</b> {cab}<br><b>Дата:</b> {date_short}<br>Нет данных"
                    )
                hover_x.append(date_short)
                hover_y.append(cab)
                continue

            # Группируем записи по специализации, суммируем часы
            spec_hours = {}
            spec_periods = {}
            spec_doctors = {}
            for r in records:
                sp = r['spec']
                spec_hours[sp] = spec_hours.get(sp, 0.0) + r['hours']
                spec_periods.setdefault(sp, []).append(str(r['Период']))
                spec_doctors.setdefault(sp, []).append(r['doctor_initials'])

            # total_hours = sum(spec_hours.values())
            # # Нормируем: 12ч = 100% высоты ячейки
            # filled_ratio = min(total_hours / MAX_HOURS, 1.0)
            # empty_ratio = 1.0 - filled_ratio

            # # Рисуем сектора сверху вниз
            # current_y = y0_cell
            # period_parts = []
            # doctor_parts = []
            # spec_parts = []

            # for sp, hrs in spec_hours.items():
            #     ratio = (hrs / MAX_HOURS) if total_hours > 0 else 0
            #     ratio = min(ratio, 1.0)
            #     if filled_ratio > 0:
            #         ratio = ratio / (total_hours / MAX_HOURS) * filled_ratio
            #     else:
            #         ratio = 0     
            #     y_bottom = current_y + ratio
            #     if y_bottom > y1_cell:
            #         y_bottom = y1_cell

            total_hours = sum(spec_hours.values())

            # ============================================================
            # ЗАГРУЖЕННОСТЬ:
            # 12 часов = 100%
            # Нормативный интервал: 08:00–20:00
            # Всё, что больше 12 часов, не увеличивает заполнение.
            # ============================================================
            filled_hours = min(total_hours, MAX_HOURS)
            filled_ratio = filled_hours / MAX_HOURS
            empty_ratio = 1.0 - filled_ratio

            # Рисуем сектора специализаций внутри заполненной части
            current_y = y0_cell
            period_parts = []
            doctor_parts = []
            spec_parts = []

            for sp, hrs in spec_hours.items():

                # Доля данной специализации от общего фактического времени.
                # Например:
                # 6 ч из 12 ч -> 50% заполненной части
                # 8 ч из 16 ч -> 50% заполненной части
                #
                # При этом сама ячейка ограничена максимумом 12 часов.
                if total_hours > 0:
                    ratio = (hrs / total_hours) * filled_ratio
                else:
                    ratio = 0.0

                y_bottom = current_y + ratio

                if y_bottom > y1_cell:
                    y_bottom = y1_cell

                shapes.append(dict(
                    type='rect',
                    x0=x0,
                    x1=x1,
                    y0=current_y,
                    y1=y_bottom,
                    fillcolor=colors.get(sp, '#999'),
                    line=dict(width=0),
                    layer='above'
                ))

                current_y = y_bottom

                period_parts.append(
                    f"{sp}: {'; '.join(dict.fromkeys(spec_periods[sp]))}"
                )

                docs = ', '.join(dict.fromkeys(spec_doctors[sp]))
                doctor_parts.append(f"{sp}: {docs}")

                spec_parts.append(f"{sp} ({hrs:.1f}ч)")

            # Остаток — серый (Пусто)
            
            if empty_ratio > 0.001:
                shapes.append(dict(
                    type='rect',
                    x0=x0, x1=x1, y0=current_y, y1=y1_cell,
                    fillcolor=EMPTY_COLOR,
                    line=dict(width=0),
                    layer='above'
                ))

            # Внешняя рамка ячейки
            shapes.append(dict(
                type='rect',
                x0=x0, x1=x1, y0=y0_cell, y1=y1_cell,
                fillcolor='rgba(0,0,0,0)',
                line=dict(width=BORDER_WIDTH, color=BORDER_COLOR),
                layer='above'
            ))

            hover_x.append(date_short)
            hover_y.append(cab)
            hover_text.append(
                f"<b>Кабинет:</b> {cab}<br>"
                f"<b>Дата:</b> {date_short}<br>"
                f"<b>Время:</b><br>{'<br>'.join(period_parts)}<br>"
                f"<b>Специализации:</b> {', '.join(spec_parts)}<br>"
                f"<b>Врач(и):</b><br>{'<br>'.join(doctor_parts)}<br>"
                f"<b>Всего часов:</b> {total_hours:.1f}"
            )

    n_rows = len(all_cabs)
    n_cols = len(all_dates)

    if n_rows == 0 or n_cols == 0:
        fig = go.Figure()
        fig.update_layout(title="Нет данных для отображения")
        return fig

    height = max(n_rows * CELL_SIZE + 160, 200)
    width = max(n_cols * CELL_SIZE + 120, 400)

    fig = go.Figure()

    # Невидимые scatter-маркеры для hover
    fig.add_trace(go.Scatter(
        x=hover_x,
        y=hover_y,
        mode='markers',
        marker=dict(
            symbol='square',
            size=MARKER_SIZE,
            color='rgba(0,0,0,0)',
        ),
        hovertext=hover_text,
        hoverinfo='text',
        showlegend=False,
    ))

    fig.update_layout(
        title='📅 Обзорный график',
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
            showgrid=False,
        ),
        xaxis=dict(
            categoryorder='array',
            categoryarray=all_dates,
            dtick=1,
            showgrid=False,
            type='category',
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(size=12),
        margin=dict(l=80, r=40, t=60, b=100),
        showlegend=False,
        shapes=shapes,
    )
    return fig


def create_hourly_heatmap(df, selected_date, selected_cabinets, colors):
    df_day = df[(df['date_str'] == selected_date) &
                df['Кабинет'].isin(selected_cabinets)].copy()

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

    def dull_color(hex_color, factor=0.4):
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        r = int(r + (255 - r) * factor)
        g = int(g + (255 - g) * factor)
        b = int(b + (255 - b) * factor)
        return f'#{r:02x}{g:02x}{b:02x}'

    VOWELS = 'аеёиоуыэюяАЕЁИОУЫЭЮЯ'
    SPECIAL_KEYWORDS = ['кабинет', 'стационар', 'хирургия', 'операционная', 'рентген', 'перевязочная']

    def is_special(name):
        if not name:
            return False
        return any(kw in name.lower() for kw in SPECIAL_KEYWORDS)

    def abbreviate(name):
        if not name:
            return ''
        s_lower = name.lower()
        if 'операционная' in s_lower:
            return 'о'
        if 'перевязочная' in s_lower:
            return 'пк.'
        if 'кабинет' in s_lower or 'стационар' in s_lower:
            words = name.split()
            return ''.join(w[0].lower() for w in words if w)
        if len(name) >= 4 and name[1] in VOWELS and name[2] in VOWELS:
            return name[:4]
        elif len(name) >= 3 and name[2] in VOWELS:
            return name[:2] + '.'
        elif len(name) >= 3:
            return name[:3] + '.'
        elif len(name) == 2:
            return name[:2] + '.'
        elif len(name) == 1:
            return name[0] + '.'
        return ''

    cell_data = {}
    for _, r in df_day.iterrows():
        for h in hours:
            if is_working(r, h):
                key = (r['Кабинет'], h)
                cell_data.setdefault(key, []).append(r)

    needs_split = set()
    for (cab, h), entries in cell_data.items():
        special_count = sum(1 for e in entries if is_special(e['surname']))
        normal_count = len(entries) - special_count
        if special_count >= 1 and normal_count >= 2:
            needs_split.add(cab)

    display_cells = []

    for (cab, h), entries in cell_data.items():
        if cab in needs_split:
            special = [e for e in entries if is_special(e['surname'])]
            normal = [e for e in entries if not is_special(e['surname'])]

            used_normals = set()
            sub_idx = 1

            for s_entry in special:
                matching = []
                for n_entry in normal:
                    if n_entry.name not in used_normals and n_entry['spec'].lower() in s_entry['surname'].lower():
                        matching.append(n_entry)
                        used_normals.add(n_entry.name)

                docs = [s_entry['doctor_initials']] + [m['doctor_initials'] for m in matching]
                docs_unique = list(dict.fromkeys(docs))
                txt = ', '.join(docs_unique)

                if matching:
                    display_text = abbreviate(matching[0]['surname'])
                    base_spec = matching[0]['spec']
                    cell_color = colors.get(base_spec, '#999')
                else:
                    display_text = abbreviate(s_entry['surname'])
                    base_spec = s_entry['spec']
                    if 'перевязочная' in s_entry['surname'].lower():
                        cell_color = dull_color(colors.get(base_spec, '#999'), 0.4)
                    else:
                        cell_color = colors.get(base_spec, '#999')

                display_cells.append({
                    'x': h,
                    'y': f"{cab}.{sub_idx}",
                    'color': cell_color,
                    'text': display_text,
                    'hover': (
                        f"<b>Кабинет:</b> {cab}.{sub_idx}<br>"
                        f"<b>Время:</b> {h}<br>"
                        f"<b>Специализация:</b> {base_spec}<br>"
                        f"<b>Врач:</b> {txt}"
                    )
                })
                sub_idx += 1

            unused = [e for e in normal if e.name not in used_normals]
            if unused:
                specs = [u['spec'] for u in unused]
                docs = list(dict.fromkeys([u['doctor_initials'] for u in unused]))
                txt = ', '.join(docs)

                display_cells.append({
                    'x': h,
                    'y': f"{cab}.{sub_idx}",
                    'color': colors.get(specs[0], '#999'),
                    'text': abbreviate(unused[0]['surname']),
                    'hover': (
                        f"<b>Кабинет:</b> {cab}.{sub_idx}<br>"
                        f"<b>Время:</b> {h}<br>"
                        f"<b>Специализация:</b> {specs[0]}<br>"
                        f"<b>Врач:</b> {txt}"
                    )
                })

        else:
            normal = [e for e in entries if not is_special(e['surname'])]
            special = [e for e in entries if is_special(e['surname'])]

            docs = list(dict.fromkeys([e['doctor_initials'] for e in entries]))
            txt = ', '.join(docs)

            if normal:
                base_spec = normal[0]['spec']
                cell_color = colors.get(base_spec, '#999')
                display_text = abbreviate(normal[0]['surname'])
            elif special:
                base_spec = special[0]['spec']
                if 'перевязочная' in special[0]['surname'].lower():
                    cell_color = dull_color(colors.get(base_spec, '#999'), 0.4)
                else:
                    cell_color = colors.get(base_spec, '#999')
                display_text = abbreviate(special[0]['surname'])
            else:
                base_spec = 'Прочее'
                cell_color = colors.get('Прочее', '#999')
                display_text = ''

            display_cells.append({
                'x': h,
                'y': str(cab),
                'color': cell_color,
                'text': display_text,
                'hover': (
                    f"<b>Кабинет:</b> {cab}<br>"
                    f"<b>Время:</b> {h}<br>"
                    f"<b>Специализация:</b> {base_spec}<br>"
                    f"<b>Врач:</b> {txt}"
                )
            })

    base_cabs = set(str(c) for c in selected_cabinets)
    split_cabs = set(c['y'] for c in display_cells if '.' in str(c['y']))
    final_cabs = (base_cabs - set(str(c) for c in needs_split)) | split_cabs
    all_display_y = sorted(final_cabs, key=cabinet_sort_key)

    filled = set((c['x'], c['y']) for c in display_cells)
    for cab in all_display_y:
        for h in hours:
            if (h, cab) not in filled:
                display_cells.append({
                    'x': h,
                    'y': cab,
                    'color': colors.get('Пусто', '#999'),
                    'text': '',
                    'hover': f"<b>Кабинет:</b> {cab}<br><b>Время:</b> {h}<br>Пусто"
                })

    display_cells.sort(key=lambda c: (cabinet_sort_key(c['y']), c['x']))

    x_list = [c['x'] for c in display_cells]
    y_list = [c['y'] for c in display_cells]
    c_list = [c['color'] for c in display_cells]
    t_list = [c['text'] for c in display_cells]
    h_list = [c['hover'] for c in display_cells]

    n_rows = len(all_display_y)
    n_cols = len(hours)

    if n_rows == 0 or n_cols == 0:
        fig = go.Figure()
        fig.update_layout(title="Нет данных для отображения")
        return fig

    height = max(n_rows * CELL_SIZE + 160, 200)
    width = max(n_cols * CELL_SIZE + 120, 400)

    fig = go.Figure(data=go.Scatter(
        x=x_list,
        y=y_list,
        mode='markers+text',
        marker=dict(
            symbol='square',
            size=MARKER_SIZE,
            color=c_list,
            line=dict(width=BORDER_WIDTH, color=BORDER_COLOR),
        ),
        text=t_list,
        textposition='middle center',
        textfont=dict(size=13, color='white'),
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
            categoryarray=all_display_y,
            autorange='reversed',
            dtick=1,
            showgrid=False,
        ),
        xaxis=dict(
            categoryorder='array',
            categoryarray=hours,
            dtick=1,
            showgrid=False,
            tickangle=45,
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(size=12),
        margin=dict(l=80, r=40, t=60, b=100),
        showlegend=False,
    )
    return fig


# ==================== ПРИЛОЖЕНИЕ ====================
def main():
    uploaded_file = st.file_uploader(
        "📁 Загрузите отчёт Excel ( .xlsx)", type=['xlsx', 'xls']
    )

    if uploaded_file is None:
        st.info("👆 Загрузите файл с отчётом о загрузке кабинетов.")
        return

    file_bytes = uploaded_file.read()
    clinic_name = extract_clinic_name(file_bytes)

    if clinic_name:
        st.markdown(f"# 🏥 График загрузки кабинетов ({clinic_name})")
    else:
        st.markdown("# 🏥 График загрузки кабинетов")

    st.markdown(
        "<p style='color:#666; font-size:1.05rem;'>"
        "Цвет ячейки = <b>специализация</b> (сектора пропорционально часам) &nbsp;|&nbsp; "
        "12 ч = вся ячейка закрашена &nbsp;|&nbsp; "
        "Незанятое время = <b>серый сектор</b> &nbsp;|&nbsp; "
        "Наведите для подробностей &nbsp;|&nbsp; "
        "Белый = <b>Нет данных</b>"
        "</p>",
        unsafe_allow_html=True,
    )

    with st.spinner('⏳ Читаем и обрабатываем данные…'):
        df = parse_excel_new(file_bytes)

    if df.empty:
        st.error("❌ Не удалось распознать данные. Проверьте формат файла.")
        return

    selected_cabinets = sorted(df['Кабинет'].unique(), key=cabinet_sort_key)

    all_specs = sorted(df['spec'].unique())
    if 'Пусто' not in all_specs:
        all_specs = ['Пусто'] + all_specs
    if 'Нет данных' not in all_specs:
        all_specs = ['Нет данных'] + all_specs
    colors = assign_colors(all_specs)

    # Список реальных специализаций для фильтра.
    # "Пусто" и "Нет данных" — состояния ячеек, а не специализации.
    available_specs = sorted(
        [spec for spec in df['spec'].unique() if spec not in ('Пусто', 'Нет данных')]
    )

    with st.sidebar:
        st.header("⚙️ Фильтры")

        mode = st.radio(
            "Режим:",
            ["⏰ Детально по часам", "📅 Обзор по периодам"],
            index=0,
        )

        selected_specs = st.multiselect(
            "Фильтр по специализациям:",
            options=available_specs,
            default=available_specs,
            placeholder="Все специализации",
            help="Можно выбрать одну или несколько специализаций. По умолчанию выбраны все.",
        )

        # Фильтр применяется до построения любого из двух графиков.
        df_filtered = df[df['spec'].isin(selected_specs)].copy()
    
        all_dates_full = df.sort_values("date_parsed")["date_str"].unique().tolist()
        all_dates_short = df.sort_values("date_parsed")["date_short"].unique().tolist()
    
        if mode == "📅 Обзор по периодам":
    
            if len(all_dates_full) > 0:
                min_date = datetime.strptime(all_dates_full[0], "%d.%m.%Y").date()
                max_date = datetime.strptime(all_dates_full[-1], "%d.%m.%Y").date()
            else:
                min_date = datetime.now().date()
                max_date = datetime.now().date()
    
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
                    date_list.append(current.strftime("%d.%m"))
                    current += timedelta(days=1)
    
                selected_dates = date_list
                date_range_label = f"{selected_dates[0]} – {selected_dates[-1]}"
    
            else:
                selected_dates = all_dates_short
                date_range_label = f"{selected_dates[0]} – {selected_dates[-1]}"
    
            selected_date = None
    
        else:
    
            if "hourly_date_index" not in st.session_state:
                st.session_state.hourly_date_index = 0
    
            if all_dates_full:
                st.session_state.hourly_date_index = max(
                    0,
                    min(
                        st.session_state.hourly_date_index,
                        len(all_dates_full) - 1,
                    ),
                )
    
                selected_date = st.selectbox(
                    "Дата:",
                    all_dates_full,
                    index=st.session_state.hourly_date_index,
                )
    
                st.session_state.hourly_date_index = all_dates_full.index(selected_date)
        
                selected_dates = []
                date_range_label = selected_date

        st.divider()
        st.markdown("**🩺 Легенда:**")
        for spec in selected_specs:
            if spec == 'Администрация':
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


    if mode == "📅 Обзор по периодам":
        if not selected_dates:
            st.info("📭 В выбранном диапазоне нет дат для отображения.")
        else:
            st.subheader(
                f"📅 Обзор с {date_range_label} ({len(selected_dates)} дн.)"
            )

            fig = create_overview_heatmap(
                df_filtered,
                selected_cabinets,
                selected_dates,
                colors
            )

            st.plotly_chart(
                fig,
                use_container_width=False
            )

            with st.expander("📊 Таблица данных"):
                show = df_filtered[
                    df_filtered['Кабинет'].isin(selected_cabinets) &
                    df_filtered['date_short'].isin(
                        [d for d in selected_dates if d in df_filtered['date_short'].values]
                    )
                ][
                    ['date_str', 'Кабинет', 'doctor_initials', 'spec', 'Период', 'hours']
                ]

                show = show.rename(columns={
                    'date_str': 'Дата',
                    'doctor_initials': 'Врач',
                    'spec': 'Специализация',
                    'hours': 'Часы',
                })

                show['_sort_key'] = show['Кабинет'].map(cabinet_sort_key)

                show = show.sort_values(
                    ['Дата', '_sort_key', 'Период']
                ).drop(columns=['_sort_key'])

                st.dataframe(
                    show,
                    use_container_width=True,
                    hide_index=True
                )

    else:
        st.subheader(f"⏰ Почасовая карта — {selected_date}")

        # ============================================================
        # НАВИГАЦИЯ ПО ДНЯМ
        # ============================================================

        current_index = st.session_state.hourly_date_index
        total_dates = len(all_dates_full)

        col_prev, col_next, col_space = st.columns([1.5, 1.5, 7])

        with col_prev:
            previous_day = st.button(
                "← Предыдущий день",
                disabled=(current_index <= 0),
                use_container_width=True,
                key="hourly_previous_day"
            )

        with col_next:
            next_day = st.button(
                "Следующий день →",
                disabled=(current_index >= total_dates - 1),
                use_container_width=True,
                key="hourly_next_day"
            )

        if previous_day:
            st.session_state.hourly_date_index -= 1
            st.rerun()

        if next_day:
            st.session_state.hourly_date_index += 1
            st.rerun()

        # ============================================================
        # ПОЧАСОВАЯ КАРТА
        # ============================================================

        fig = create_hourly_heatmap(
            df_filtered,
            selected_date,
            selected_cabinets,
            colors
        )

        st.plotly_chart(
            fig,
            use_container_width=False
        )

        with st.expander("📊 Таблица данных за день"):
            df_day = df_filtered[df_filtered['date_str'] == selected_date]

            show = df_day[
                df_day['Кабинет'].isin(selected_cabinets)
            ][
                ['Кабинет', 'doctor_initials', 'spec', 'Период', 'hours']
            ]

            show = show.rename(columns={
                'doctor_initials': 'Врач',
                'spec': 'Специализация',
                'hours': 'Часы',
            })

            show['_sort_key'] = show['Кабинет'].map(cabinet_sort_key)

            show = show.sort_values(
                ['_sort_key', 'Период']
            ).drop(columns=['_sort_key'])

            st.dataframe(
                show,
                use_container_width=True,
                hide_index=True
            )


if __name__ == "__main__":
    main()
