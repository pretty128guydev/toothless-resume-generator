#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import json
import re
from pathlib import Path

SECTION_TITLES = {
    'Профессиональный профиль': 'about me',
    'ПРОФЕССИОНАЛЬНОЕ РЕЗЮМЕ': 'about me',
    'ОБО МНЕ': 'about me',
    'О себе': 'about me',
    'Навыки': 'skills',
    'Ключевые навыки': 'skills',
    'КЛЮЧЕВЫЕ НАВЫКИ': 'skills',
    'ТЕХНИЧЕСКИЕ НАВЫКИ': 'skills',
    'Дополнительно': 'skills',
    'ДОПОЛНИТЕЛЬНО': 'skills',
    'Опыт работы': 'work experience',
    'ОПЫТ РАБОТЫ': 'work experience',
    'КОММЕРЧЕСКИЙ ОПЫТ': 'work experience',
    'Образование': 'education',
    'ОБРАЗОВАНИЕ': 'education',
    'Сопроводительное письмо': 'cover letter',
    'СОПРОВОДИТЕЛЬНОЕ ПИСЬМО': 'cover letter',
    'Короткое сопроводительное письмо': 'cover letter'
}

KNOWN_COMPANIES = {
    'SMARTER HOLDINGS INTERNATIONAL LTD',
    'LANDINGDV',
    'INSIDE 360',
    'ООО «ДИАСОФТ»',
    'ООО "ДИАСОФТ"',
    'ДИАСОФТ',
    'RETAILOS',
    'TECHAHEADLAB',
    'TECHAHEADLAB (USA)',
    'TECHAHEADLAB USA'
}


def _norm_heading(s: str) -> str:
    return re.sub(r'\s+', ' ', s.strip()).upper()


def _normalize_lines(text: str):
    lines = [line.strip() for line in text.splitlines()]
    # keep blank lines for paragraph separation
    return lines


def _split_sections(lines):
    sections = {}
    current = None
    buf = []
    heading_lookup = {_norm_heading(k): k for k in SECTION_TITLES.keys()}
    for line in lines:
        norm = _norm_heading(line)
        if norm in heading_lookup:
            if current:
                sections[current] = buf[:]
            current = heading_lookup[norm]
            buf = []
            continue
        buf.append(line)
    if current:
        sections[current] = buf[:]
    return sections


def _parse_about(section_lines):
    paragraphs = []
    buf = []
    for line in section_lines:
        if not line:
            if buf:
                paragraphs.append(' '.join(buf).strip())
                buf = []
            continue
        buf.append(line)
    if buf:
        paragraphs.append(' '.join(buf).strip())
    return [p for p in paragraphs if p]


def _parse_skills(section_lines):
    skills = []
    for line in section_lines:
        if not line:
            continue
        if ':' in line:
            label, rest = line.split(':', 1)
            label = label.strip()
            rest = rest.strip()
            if rest:
                skills.append(f"{label}: {rest}")
        else:
            skills.append(line)
    return skills


def _parse_education(section_lines):
    # Expect pattern:
    # Бакалавр, 2016
    # Университет
    # Направление: ...
    entries = []
    buf = [line for line in section_lines if line]
    if not buf:
        return entries

    degree_line = buf[0]
    institution = buf[1] if len(buf) > 1 else ''
    rest = buf[2:] if len(buf) > 2 else []

    period = ''
    m = re.search(r'(\d{4})\s*[-–—]\s*(\d{4})', degree_line)
    if m:
        period = f"{m.group(1)}-{m.group(2)}"
    else:
        m = re.search(r'(\d{4})', degree_line)
        if m:
            period = m.group(1)

    degree = degree_line.strip()
    if rest:
        degree = ' '.join(rest).strip()

    entries.append({
        'institution': institution,
        'period': period,
        'degree': degree
    })
    return entries


def _parse_work_experience(section_lines):
    # Heuristic parser for formats:
    # A) Role
    #    Company
    #    Period (e.g. Июнь 2023 по Сентябрь 2025)
    #    bullets...
    # B) Company — Role
    #    Period
    #    bullets...
    lines = [l for l in section_lines if l.strip() != '']
    jobs = []
    months = r'(Январ|Феврал|Март|Апрел|Май|Июн|Июл|Август|Сентябр|Октябр|Ноябр|Декабр)'
    period_re = re.compile(rf'{months}.*\d{{4}}.*(по|—|–|-).*{months}.*\d{{4}}', re.IGNORECASE)
    years_re = re.compile(r'\b\d{4}\s*(по|—|–|-)\s*\d{4}\b', re.IGNORECASE)

    def is_company_line(line: str) -> bool:
        norm = _norm_heading(line)
        if norm in KNOWN_COMPANIES:
            return True
        if re.search(r'\b(LLC|LTD|INC|ООО|АО|ЗАО)\b', norm):
            return True
        return False

    def is_period(line: str) -> bool:
        return bool(period_re.search(line) or years_re.search(line))

    def is_heading(line: str) -> bool:
        return _norm_heading(line) in {_norm_heading(k) for k in SECTION_TITLES.keys()}

    def looks_like_role_line(line: str) -> bool:
        role_keywords = (
            'developer', 'engineer', 'разработчик', 'инженер', 'frontend', 'backend',
            'full-stack', 'fullstack', 'web', 'senior', 'lead', 'architect', 'архитектор'
        )
        low = line.lower()
        return any(k in low for k in role_keywords)

    def looks_like_job_start(idx: int) -> bool:
        if idx + 2 >= len(lines):
            return False
        if is_heading(lines[idx]) or is_heading(lines[idx + 1]) or is_heading(lines[idx + 2]):
            return False
        return is_period(lines[idx + 2])

    def looks_like_job_start_alt(idx: int) -> bool:
        if idx + 1 >= len(lines):
            return False
        if is_heading(lines[idx]) or is_heading(lines[idx + 1]):
            return False
        if '—' not in lines[idx]:
            return False
        if not is_period(lines[idx + 1]):
            return False
        # avoid treating bullet-like statements as job headers
        left = lines[idx].split('—', 1)[0].strip()
        if not is_company_line(left):
            return False
        return True

    def looks_like_job_start_company_first(idx: int) -> bool:
        if idx + 2 >= len(lines):
            return False
        if is_heading(lines[idx + 1]) or is_heading(lines[idx + 2]):
            return False
        if not is_period(lines[idx + 2]):
            return False
        # company line can be any name if role line looks valid
        if looks_like_role_line(lines[idx + 1]):
            return True
        return is_company_line(lines[idx])

    def looks_like_job_start_company_period_role(idx: int) -> bool:
        if idx + 2 >= len(lines):
            return False
        if is_heading(lines[idx + 1]) or is_heading(lines[idx + 2]):
            return False
        if not is_company_line(lines[idx]):
            return False
        if not is_period(lines[idx + 1]):
            return False
        return looks_like_role_line(lines[idx + 2])

    i = 0
    while i < len(lines):
        if is_heading(lines[i]):
            i += 1
            continue
        if looks_like_job_start_alt(i):
            comp_role = lines[i].strip()
            period = lines[i + 1].strip()
            company = ''
            role = ''
            if '—' in comp_role:
                parts = [p.strip() for p in comp_role.split('—', 1)]
                company = parts[0]
                role = parts[1] if len(parts) > 1 else ''
            i += 2
        elif looks_like_job_start_company_period_role(i):
            company = lines[i].strip()
            period = lines[i + 1].strip()
            role = lines[i + 2].strip()
            i += 3
        elif looks_like_job_start_company_first(i):
            company = lines[i].strip()
            role = lines[i + 1].strip()
            period = lines[i + 2].strip()
            i += 3
        elif looks_like_job_start(i):
            role = lines[i].strip()
            company = lines[i + 1].strip()
            period = lines[i + 2].strip()
            i += 3
        else:
            i += 1
            continue

        bullets = []
        while i < len(lines):
            if looks_like_job_start(i):
                break
            if is_heading(lines[i]):
                break
            bullets.append(lines[i])
            i += 1

        jobs.append({
            'company name': company,
            'role': role,
            'period': period,
            'experience': [b for b in bullets if b]
        })

    return jobs


def parse_text(text: str):
    lines = _normalize_lines(text)
    sections = _split_sections(lines)

    data = {
        'name': 'Игнатов Сергей Николаевич',
        'address': 'Владивосток, Россия',
        'email': 'cenergiy408@gmail.com',
        'telegram_address': '@ignatov_110104',
    }

    # About sections
    about = []
    if 'ОБО МНЕ' in sections:
        about.extend(_parse_about(sections['ОБО МНЕ']))
    elif 'О себе' in sections:
        about.extend(_parse_about(sections['О себе']))
    elif 'Профессиональный профиль' in sections:
        about.extend(_parse_about(sections['Профессиональный профиль']))
    elif 'ПРОФЕССИОНАЛЬНОЕ РЕЗЮМЕ' in sections:
        about.extend(_parse_about(sections['ПРОФЕССИОНАЛЬНОЕ РЕЗЮМЕ']))
    if about:
        data['about me'] = about

    # Work experience
    if 'КОММЕРЧЕСКИЙ ОПЫТ' in sections:
        data['work experience'] = _parse_work_experience(sections['КОММЕРЧЕСКИЙ ОПЫТ'])
    elif 'Опыт работы' in sections:
        data['work experience'] = _parse_work_experience(sections['Опыт работы'])
    elif 'ОПЫТ РАБОТЫ' in sections:
        data['work experience'] = _parse_work_experience(sections['ОПЫТ РАБОТЫ'])

    # Education
    # Use fixed education entry regardless of input text
    data['education'] = [
        {
            'institution': 'Саратовский государственный технический университет',
            'period': '1997 - 2002',
            'degree': 'Специалитет: инженер по прикладной информатике'
        }
    ]

    # Skills
    skills = []
    if 'Навыки' in sections:
        skills.extend(_parse_skills(sections['Навыки']))
    if 'Ключевые навыки' in sections:
        skills.extend(_parse_skills(sections['Ключевые навыки']))
    if 'КЛЮЧЕВЫЕ НАВЫКИ' in sections:
        skills.extend(_parse_skills(sections['КЛЮЧЕВЫЕ НАВЫКИ']))
    if 'ТЕХНИЧЕСКИЕ НАВЫКИ' in sections:
        skills.extend(_parse_skills(sections['ТЕХНИЧЕСКИЕ НАВЫКИ']))
    if 'Дополнительно' in sections:
        skills.extend(_parse_skills(sections['Дополнительно']))
    if 'ДОПОЛНИТЕЛЬНО' in sections:
        skills.extend(_parse_skills(sections['ДОПОЛНИТЕЛЬНО']))
    if skills:
        data['skills'] = skills

    # Cover letter
    if 'Сопроводительное письмо' in sections:
        data['cover letter'] = _parse_about(sections['Сопроводительное письмо'])
    elif 'СОПРОВОДИТЕЛЬНОЕ ПИСЬМО' in sections:
        data['cover letter'] = _parse_about(sections['СОПРОВОДИТЕЛЬНОЕ ПИСЬМО'])
    elif 'Короткое сопроводительное письмо' in sections:
        data['cover letter'] = _parse_about(sections['Короткое сопроводительное письмо'])

    # Drop leading non-letterhead line if it looks like a preface
    if 'cover letter' in data and data['cover letter']:
        if data['cover letter'][0].lower().startswith('теперь подготовим'):
            data['cover letter'] = data['cover letter'][1:]

    return data


def main():
    parser = argparse.ArgumentParser(description='Parse resume text into sample_input.json format')
    parser.add_argument('input', help='Path to input text file')
    parser.add_argument('--output', '-o', default='sample_input.json', help='Output JSON path')
    args = parser.parse_args()

    text = Path(args.input).read_text(encoding='utf-8')
    data = parse_text(text)

    Path(args.output).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Wrote JSON: {args.output}')


if __name__ == '__main__':
    main()
