import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, time, timedelta
import re

st.set_page_config(page_title="График загрузки кабинетов", layout="wide")

# ==================== ЕДИНЫЙ СТИЛЬ ====================
CELL_SIZE = 46          # сторона клетки в пикселях
MARKER_SIZE = 42        # сторона квадрата (зазор 4px)
BORDER_WIDTH = 1.5
BORDER_COLOR = '#444444'

# ==================== НОРМАЛИЗАЦИЯ ====================
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


# ==================== ИЗВЛЕЧЕНИЕ НАЗВАНИЯ КЛИНИКИ ====================
def clean_clinic_name(name):
    if pd.isna(name):
        return ''
    name = str(name).strip()

    # Удаляем числовые коды в начале/конце (001, 123 и т.д.)
    name = re.sub(r'^\d{2,}\s*[-–—.]?\s*', '', name)
    name = re.sub(r'\s*[-–—.]?\s*\d{2,}$', '', name)

    # Удаляем формы собственности и технические аббревиатуры
    forms = [
        'ООО', 'ОАО', 'ЗАО', 'АО', 'ИП', 'ПАО', 'НАО',
        'ФГБУ', 'ФГАОУ', 'ФГБОУ', 'ФГАУ', 'МБУ', 'ГБУ',
        'ГБУЗ', 'МБУЗ', 'ФМБА', 'МИНЗДРАВ'
    ]
    for form in forms:
        name = re.sub(rf'\b{re.escape(form)}\b', '', name, flags=re.IGNORECASE)

    # Убираем лишние знаки препинания по краям
    name = re.sub(r'^[.,;:\-\s]+', '', name)
    name = re.sub(r'[.,;:\-\s]+$', '', name)
    # Схлопываем множественные пробелы
    name = re.sub(r'\s+', ' ', name).strip()

    return name


def extract_clinic_name(uploaded_file):
    """Извлекает название клиники из первых строк Листа 2."""
    try:
        df_raw = pd.read_excel(uploaded_file, sheet_name='Лист2', header=None, nrows=15)
    except Exception:
        try:
            df_raw = pd.read_excel(uploaded_file, sheet_name=0, header=None, nrows=15)
        except Exception:
            return ''

    candidates = []
    for col in df_raw.columns:
        for val in df_raw[col].dropna():
            s = str(val).strip()
            # Ищем осмысленный текст достаточной длины
            if len(s) >= 5 and not s.lower().startswith('http') and not s.replace('.', '').replace(',', '').isdigit():
                candidates.append(s)

    if not candidates:
        return ''

    # Самая длинная строка — скорее всего название клиники
    raw_name = max(candidates, key=len)
    return clean_clinic_name(raw_name)


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
    s = str(c)
    parts = s.split('.')
    try:
        main = int(parts[0])
    except ValueError:
        return (1, s, 0)
    sub = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    return (0, main, sub)


def create_overview_heatmap(df, selected_cabinets, selected_dates, colors):
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

    n_rows = len(all_cabs)
    n_cols = len(all_dates)
    height = n_rows * CELL_SIZE + 160   # 60 top + 100 bottom
    width = n_cols * CELL_SIZE + 120    # 80 left + 40 right

    fig = go.Figure(data=go.Scatter(
        x=x_list,
        y=y_list,
        mode='markers',
        marker=dict(
            symbol='square',
            size=MARKER_SIZE,
            color=c_list,
            line=dict(width=BORDER_WIDTH, color=BORDER_COLOR),
        ),
        hovertext=h_list,
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

    # === 1. Собираем записи по каждой клетке ===
    cell_data = {}
    for _, r in df_day.iterrows():
        for h in hours:
            if is_working(r, h):
                key = (r['Кабинет'], h)
                cell_data.setdefault(key, []).append(r)

    # === 2. Определяем, какие кабинеты нужно разделить на весь день ===
    # Разбиваем ТОЛЬКО если в каком-то часу есть special + 2+ обычных врача
    needs_split = set()
    for (cab, h), entries in cell_data.items():
        special_count = sum(1 for e in entries if is_special(e['surname']))
        normal_count = len(entries) - special_count
        if special_count >= 1 and normal_count >= 2:
            needs_split.add(cab)

    # === 3. Формируем клетки ===
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

                docs = [s_entry['surname']] + [m['surname'] for m in matching]
                docs_unique = list(dict.fromkeys(docs))
                txt = ', '.join(docs_unique)

                if matching:
                    display_text = abbreviate(matching[0]['surname'])
                    base_spec = matching[0]['spec']
                    cell_color = colors.get(base_spec, '#999')  # цвет ВРАЧА, обычный
                else:
                    display_text = abbreviate(s_entry['surname'])
                    base_spec = s_entry['spec']
                    # Только перевязочная — светлый
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
                docs = list(dict.fromkeys([u['surname'] for u in unused]))
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
            # === НЕ разбиваем ===
            normal = [e for e in entries if not is_special(e['surname'])]
            special = [e for e in entries if is_special(e['surname'])]

            docs = list(dict.fromkeys([e['surname'] for e in entries]))
            txt = ', '.join(docs)

            if normal:
                # Есть врач — цвет врача, обычный
                base_spec = normal[0]['spec']
                cell_color = colors.get(base_spec, '#999')
                display_text = abbreviate(normal[0]['surname'])
            elif special:
                # Только special
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

    # === 4. Формируем ось Y: убираем разделённые базовые кабинеты ===
    base_cabs = set(str(c) for c in selected_cabinets)
    split_cabs = set(c['y'] for c in display_cells if '.' in str(c['y']))
    final_cabs = (base_cabs - set(str(c) for c in needs_split)) | split_cabs
    all_display_y = sorted(final_cabs, key=cabinet_sort_key)

    # === 5. Пустые клетки ===
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
    height = n_rows * CELL_SIZE + 160
    width = n_cols * CELL_SIZE + 120

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


# ==================== СПЕЦИАЛЬНЫЕ КАБИНЕТЫ ====================
SPECIAL_CABS = [
    "Кабинет забора мазков",
    "Кабинет повторных приемов",
    "Травмпункт Перевязочная Северная",
    "Кабинет описания ЭКГ .",
    "Кабинет описания Холтеров и СМАДов",
    "Кабинет описания спирографии",
]
SPECIAL_SPEC_MAP = {
    "Кабинет забора мазков": "Процедурные",
    "Кабинет повторных приемов": "Процедурные",
    "Травмпункт Перевязочная Северная": "Травматология",
    "Кабинет описания ЭКГ .": "Процедурные",
    "Кабинет описания Холтеров и СМАДов": "Процедурные",
    "Кабинет описания спирографии": "Процедурные",
}


def create_special_overview_heatmap(df, selected_dates, colors):
    df_f = df[df['Кабинет'].isin(SPECIAL_CABS)].copy()

    all_dates = sorted(selected_dates,
                       key=lambda x: datetime.strptime(x + '.2026', '%d.%m.%Y'))

    if not df_f.empty:
        agg = df_f.groupby(['date_short', 'Кабинет']).agg({
            'spec': lambda x: x.mode().iloc[0] if not x.mode().empty else 'Прочее',
            'surname': lambda x: ', '.join(dict.fromkeys(x)),
            'hours': 'sum',
            'Период': lambda x: '; '.join(dict.fromkeys(x)),
        }).reset_index()
    else:
        agg = pd.DataFrame(columns=['date_short', 'Кабинет', 'spec', 'surname', 'hours', 'Период'])

    grid = pd.DataFrame([(d, c) for d in all_dates for c in SPECIAL_CABS],
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

    n_rows = len(SPECIAL_CABS)
    n_cols = len(all_dates)
    height = n_rows * CELL_SIZE + 160
    width = n_cols * CELL_SIZE + 320   # больше левый отступ

    fig = go.Figure(data=go.Scatter(
        x=x_list,
        y=y_list,
        mode='markers',
        marker=dict(
            symbol='square',
            size=MARKER_SIZE,
            color=c_list,
            line=dict(width=BORDER_WIDTH, color=BORDER_COLOR),
        ),
        hovertext=h_list,
        hoverinfo='text',
        showlegend=False,
    ))

    fig.update_layout(
        title='🏥 Специальные кабинеты — обзор',
        xaxis_title='Дата',
        yaxis_title='Кабинет',
        height=height,
        width=width,
        yaxis=dict(
            type='category',
            categoryorder='array',
            categoryarray=SPECIAL_CABS,
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
        margin=dict(l=280, r=40, t=60, b=100),
        showlegend=False,
    )
    return fig


def create_special_hourly_heatmap(df, selected_date, colors):
    df_day = df[(df['date_str'] == selected_date) &
                df['Кабинет'].isin(SPECIAL_CABS)].copy()

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
    for cab in SPECIAL_CABS:
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
                spec_val = specs[0] if specs else SPECIAL_SPEC_MAP[cab]
                c_list.append(colors.get(spec_val, '#999'))
                h_list.append(
                    f"<b>Кабинет:</b> {cab}<br>"
                    f"<b>Время:</b> {hr}<br>"
                    f"<b>Специализация:</b> {spec_val}<br>"
                    f"<b>Врач:</b> {txt}"
                )
            else:
                c_list.append(colors.get('Пусто', '#999'))
                h_list.append(f"<b>Кабинет:</b> {cab}<br><b>Время:</b> {hr}<br>Пусто")

    n_rows = len(SPECIAL_CABS)
    n_cols = len(hours)
    height = n_rows * CELL_SIZE + 160
    width = n_cols * CELL_SIZE + 320

    fig = go.Figure(data=go.Scatter(
        x=x_list,
        y=y_list,
        mode='markers',
        marker=dict(
            symbol='square',
            size=MARKER_SIZE,
            color=c_list,
            line=dict(width=BORDER_WIDTH, color=BORDER_COLOR),
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
            categoryarray=SPECIAL_CABS,
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
        margin=dict(l=280, r=40, t=60, b=100),
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

    # --- Извлекаем название клиники из файла ---
    clinic_name = extract_clinic_name(uploaded_file)
    uploaded_file.seek(0)  # сброс указателя для повторного чтения

    if clinic_name:
        st.markdown(f"# 🏥 График загрузки кабинетов ({clinic_name})")
    else:
        st.markdown("# 🏥 График загрузки кабинетов")

    st.markdown(
        "<p style='color:#666; font-size:1.05rem;'>"
        "Цвет ячейки = <b>специализация</b> &nbsp;|&nbsp; "
        "Наведите на ячейку для подробной информации &nbsp;|&nbsp; "
        "Серый = <b>Пусто</b> &nbsp;|&nbsp; "
        "Белый = <b>Нет данных</b>"
        "</p>",
        unsafe_allow_html=True,
    )

    with st.spinner('⏳ Читаем и обрабатываем данные…'):
        df = parse_excel_new(uploaded_file)

    if df.empty:
        st.error("❌ Не удалось распознать данные. Проверьте формат файла.")
        return

    selected_cabinets = [str(i) for i in range(1, 26)]

    all_specs = sorted(df['spec'].unique())
    if 'Пусто' not in all_specs:
        all_specs = ['Пусто'] + all_specs
    if 'Нет данных' not in all_specs:
        all_specs = ['Нет данных'] + all_specs
    colors = assign_colors(all_specs)

    with st.sidebar:
        st.header("⚙️ Фильтры")

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
        for spec in sorted(colors.keys()):
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
        st.subheader(f"📅 Обзор с {date_range_label} ({len(selected_dates)} дн.)")
        fig = create_overview_heatmap(df, selected_cabinets, selected_dates, colors)
        st.plotly_chart(fig, use_container_width=False)

        with st.expander("📊 Таблица данных"):
            show = df[
                df['Кабинет'].isin(selected_cabinets) &
                df['date_short'].isin([d for d in selected_dates if d in df['date_short'].values])
            ][['date_str', 'Кабинет', 'Доктор', 'spec', 'Период', 'hours']]
            show = show.sort_values(['date_str', 'Кабинет', 'Период'])
            st.dataframe(show, use_container_width=True, hide_index=True)

        # --- СПЕЦКАБИНЕТЫ: обзор по дням ---
        st.divider()
        st.subheader("🏥 Специальные кабинеты")
        fig_special = create_special_overview_heatmap(df, selected_dates, colors)
        st.plotly_chart(fig_special, use_container_width=False)

    else:
        st.subheader(f"⏰ Почасовая карта — {selected_date}")
        fig = create_hourly_heatmap(df, selected_date, selected_cabinets, colors)
        st.plotly_chart(fig, use_container_width=False)

        with st.expander("📊 Таблица данных за день"):
            df_day = df[df['date_str'] == selected_date]
            show = df_day[df_day['Кабинет'].isin(selected_cabinets)][
                ['Кабинет', 'Доктор', 'spec', 'Период', 'hours']
            ].sort_values(['Кабинет', 'Период'])
            st.dataframe(show, use_container_width=True, hide_index=True)

        # --- СПЕЦКАБИНЕТЫ: почасовая ---
        st.divider()
        st.subheader("🏥 Специальные кабинеты")
        fig_special = create_special_hourly_heatmap(df, selected_date, colors)
        st.plotly_chart(fig_special, use_container_width=False)


if __name__ == "__main__":
    main()
