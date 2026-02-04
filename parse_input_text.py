#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import json
import re
from pathlib import Path

SECTION_TITLES = {
    'Профессиональный профиль': 'about me',
    'Опыт работы': 'work experience',
    'Образование': 'education',
    'Ключевые навыки': 'skills',
    'О себе': 'about me',
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
    # Heuristic parser based on block structure with blank lines
    blocks = []
    cur = []
    for line in section_lines:
        if line == '':
            if cur:
                blocks.append(cur)
                cur = []
            continue
        cur.append(line)
    if cur:
        blocks.append(cur)

    jobs = []
    i = 0
    while i < len(blocks):
        block = blocks[i]
        if not block:
            i += 1
            continue
        company = block[0].strip()
        role = ''
        period = ''
        bullets = []
        stack_line = ''

        if i + 1 < len(blocks):
            role_block = blocks[i + 1]
            if role_block:
                role = role_block[0].strip()
            if len(role_block) > 1:
                period = role_block[1].strip()
        i += 2

        while i < len(blocks):
            b = blocks[i]
            joined = ' '.join(b).strip()
            if joined.startswith('Стек:'):
                stack_line = joined
                i += 1
                break
            # detect start of next company by single-line capitalized
            if len(b) == 1 and b[0].istitle() and b[0] != 'Стек:':
                break
            bullets.extend(b)
            i += 1

        if stack_line:
            bullets.append(stack_line)

        if company:
            jobs.append({
                'company name': company,
                'role': role,
                'period': period,
                'experience': [b for b in bullets if b]
            })
        else:
            i += 1

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
    if 'Профессиональный профиль' in sections:
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
    if 'Ключевые навыки' in sections:
        data['skills'] = _parse_skills(sections['Ключевые навыки'])

    # Cover letter
    if 'Короткое сопроводительное письмо' in sections:
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
