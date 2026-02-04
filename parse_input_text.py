#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import json
import re
from pathlib import Path

SECTION_TITLES = {
    'Профессиональный профиль': 'about me',
    'О себе': 'about me',
    'Навыки': 'skills',
    'Ключевые навыки': 'skills',
    'Опыт работы': 'work experience',
    'Образование': 'education',
    'Сопроводительное письмо': 'cover letter',
    'Короткое сопроводительное письмо': 'cover letter'
}


def _normalize_lines(text: str):
    lines = [line.strip() for line in text.splitlines()]
    # keep blank lines for paragraph separation
    return lines


def _split_sections(lines):
    sections = {}
    current = None
    buf = []
    for line in lines:
        if line in SECTION_TITLES:
            if current:
                sections[current] = buf[:]
            current = line
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
    # Heuristic parser for new format:
    # Period line
    # Company — Role line
    # bullets until next period line
    lines = [l for l in section_lines if l != '']
    jobs = []
    i = 0
    period_re = re.compile(r'\b\d{4}\b')
    while i < len(lines):
        line = lines[i]
        if not period_re.search(line):
            i += 1
            continue

        period = line.strip()
        company = ''
        role = ''
        bullets = []

        if i + 1 < len(lines):
            comp_role = lines[i + 1]
            if '—' in comp_role:
                parts = [p.strip() for p in comp_role.split('—', 1)]
                company = parts[0]
                role = parts[1] if len(parts) > 1 else ''
            else:
                company = comp_role.strip()
            i += 2
        else:
            i += 1

        while i < len(lines) and not period_re.search(lines[i]):
            bullets.append(lines[i])
            i += 1

        if company or role or bullets:
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
        'name': 'Иванов Дмитрий Александрович',
        'address': 'Санкт-Петербург',
        'email': 'dmitry@gmail.com',
        'telegram_address': '@dmitry_120804'
    }

    # About sections
    about = []
    if 'О себе' in sections:
        about.extend(_parse_about(sections['О себе']))
    elif 'Профессиональный профиль' in sections:
        about.extend(_parse_about(sections['Профессиональный профиль']))
    if about:
        data['about me'] = about

    # Work experience
    if 'Опыт работы' in sections:
        data['work experience'] = _parse_work_experience(sections['Опыт работы'])

    # Education
    # Use fixed education entry regardless of input text
    data['education'] = [
        {
            'institution': 'Тульский государственный университет',
            'period': '2012 - 2016',
            'degree': 'Бакалавр Компьютерных наук'
        }
    ]

    # Skills
    if 'Навыки' in sections:
        data['skills'] = _parse_skills(sections['Навыки'])
    elif 'Ключевые навыки' in sections:
        data['skills'] = _parse_skills(sections['Ключевые навыки'])

    # Cover letter
    if 'Сопроводительное письмо' in sections:
        data['cover letter'] = _parse_about(sections['Сопроводительное письмо'])
    elif 'Короткое сопроводительное письмо' in sections:
        data['cover letter'] = _parse_about(sections['Короткое сопроводительное письмо'])

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
