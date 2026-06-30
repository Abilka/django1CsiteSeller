from __future__ import annotations

import re
from dataclasses import dataclass, field

QUERY_KEYWORDS = (
    'ВЫБРАТЬ',
    'РАЗРЕШЕННЫЕ',
    'ПЕРВЫЕ',
    'ИЗ',
    'ГДЕ',
    'СГРУППИРОВАТЬ ПО',
    'ИМЕЮЩИЕ',
    'УПОРЯДОЧИТЬ ПО',
    'ОБЪЕДИНИТЬ ВСЕ',
    'ОБЪЕДИНИТЬ',
    'ПОМЕСТИТЬ',
    'ИНДЕКСИРОВАТЬ ПО',
    'ИТОГИ',
    'АВТОУПОРЯДОЧИВАНИЕ',
)

CLAUSE_KEYWORDS = ('ИЗ', 'ГДЕ', 'СГРУППИРОВАТЬ ПО', 'ИМЕЮЩИЕ', 'УПОРЯДОЧИТЬ ПО', 'ОБЪЕДИНИТЬ ВСЕ', 'ОБЪЕДИНИТЬ', 'ПОМЕСТИТЬ')

KEYWORD_PATTERN = re.compile(
    r'\b(' + '|'.join(re.escape(word) for word in sorted(QUERY_KEYWORDS, key=len, reverse=True)) + r')\b',
    re.IGNORECASE,
)


@dataclass
class QueryFormatResult:
    formatted: str
    warnings: list[str] = field(default_factory=list)
    line_count: int = 0


def _balance_check(text: str) -> list[str]:
    warnings: list[str] = []
    pairs = {'(': ')', '[': ']', '{': '}'}
    stack: list[str] = []
    for char in text:
        if char in pairs:
            stack.append(char)
        elif char in pairs.values():
            if not stack or pairs[stack[-1]] != char:
                warnings.append('Несбалансированные скобки в запросе.')
                break
            stack.pop()
    if stack and 'Несбалансированные скобки в запросе.' not in warnings:
        warnings.append('Несбалансированные скобки в запросе.')
    return warnings


def _normalize_whitespace(text: str) -> str:
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _split_top_level_commas(line: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    for char in line:
        if char in '([{':
            depth += 1
        elif char in ')]}':
            depth = max(depth - 1, 0)
        if char == ',' and depth == 0:
            parts.append(''.join(current).strip())
            current = []
            continue
        current.append(char)
    tail = ''.join(current).strip()
    if tail:
        parts.append(tail)
    return parts


def _format_select_block(lines: list[str]) -> list[str]:
    if not lines:
        return lines
    header = lines[0].strip()
    if not re.match(r'(?i)^ВЫБРАТЬ', header):
        return lines

    fields = _split_top_level_commas(header)
    if len(fields) <= 1:
        return lines

    prefix_match = re.match(r'(?i)^(ВЫБРАТЬ(?:\s+РАЗРЕШЕННЫЕ)?(?:\s+ПЕРВЫЕ\s+\d+)?)\s+', fields[0])
    if prefix_match:
        select_prefix = prefix_match.group(1).upper()
        first_field = fields[0][prefix_match.end():].strip()
        field_lines = [first_field] + fields[1:]
    else:
        select_prefix = 'ВЫБРАТЬ'
        field_lines = fields

    formatted = [f'{select_prefix}']
    for index, field_line in enumerate(field_lines):
        suffix = ',' if index < len(field_lines) - 1 else ''
        formatted.append(f'    {field_line}{suffix}')
    return formatted + lines[1:]


def format_query(text: str) -> QueryFormatResult:
    warnings = _balance_check(text)
    normalized = _normalize_whitespace(text)
    if not normalized:
        return QueryFormatResult(formatted='', warnings=['Введите текст запроса.'], line_count=0)

    clause_pattern = re.compile(
        r'\s+(?=(?:' + '|'.join(re.escape(keyword) for keyword in CLAUSE_KEYWORDS) + r')\b)',
        re.IGNORECASE,
    )
    expanded = clause_pattern.sub('\n', normalized)
    raw_lines = [line.strip() for line in expanded.split('\n') if line.strip()]
    output: list[str] = []
    buffer: list[str] = []

    def flush_buffer():
        nonlocal buffer
        if buffer:
            output.extend(_format_select_block(buffer))
            buffer = []

    for line in raw_lines:
        upper = line.upper()
        is_clause = any(upper.startswith(keyword) for keyword in CLAUSE_KEYWORDS)
        if is_clause and buffer:
            flush_buffer()
            output.append(KEYWORD_PATTERN.sub(lambda match: match.group(1).upper(), line))
        elif not output and not buffer and re.match(r'(?i)^ВЫБРАТЬ', line):
            buffer.append(line)
        elif buffer and not is_clause:
            buffer[-1] = f'{buffer[-1]} {line}'
        else:
            flush_buffer()
            output.append(KEYWORD_PATTERN.sub(lambda match: match.group(1).upper(), line))

    flush_buffer()
    formatted = KEYWORD_PATTERN.sub(
        lambda match: match.group(1).upper(),
        '\n'.join(output),
    )
    return QueryFormatResult(
        formatted=formatted,
        warnings=warnings,
        line_count=len(formatted.splitlines()) if formatted else 0,
    )
