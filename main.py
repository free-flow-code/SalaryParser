import os
import requests
from itertools import count
from terminaltables import AsciiTable
from dotenv import load_dotenv


def get_average_salary(salary_from, salary_to):
    if not salary_from:
        average_salary = salary_to * 0.8
    elif not salary_to:
        average_salary = salary_from * 1.2
    else:
        average_salary = (salary_from + salary_to) / 2
    return int(average_salary)


def get_page_rub_salary_hh(page_payload):
    page_salaries = []
    for vacancy in page_payload['items']:
        if vacancy['salary'] and vacancy['salary']['currency'] == 'RUR':
            salary_from = vacancy['salary']['from']
            salary_to = vacancy['salary']['to']
            vacancy_average_salary = get_average_salary(salary_from, salary_to)
            page_salaries.append(vacancy_average_salary)
    return page_salaries


def predict_rub_salary_hh(vacancy, area, period):
    url = 'https://api.hh.ru/vacancies'
    headers = {'User-Agent': 'Mozilla/5.0'}
    params = {
        'text': vacancy,
        'area': area,
        'period': period,
        'only_with_salary': True,
        'page': 0
    }
    vacancies_found = 0
    vacancies_processed = 0
    all_pages_salaries = []
    for page in count():
        params['page'] = page
        try:
            page_response = requests.get(url, params=params, headers=headers)
            page_response.raise_for_status()
        except requests.exceptions.HTTPError:
            continue
        page_payload = page_response.json()
        pages_number = page_payload['pages']
        one_page_salaries = get_page_rub_salary_hh(page_payload)
        vacancies_processed += len(one_page_salaries)
        all_pages_salaries.extend(one_page_salaries)

        if page == pages_number - 1:
            vacancies_found = page_payload['found']
            break
    vacancy_stats_hh = {
        'vacancies_found': vacancies_found,
        'vacancies_processed': vacancies_processed
    }
    try:
        vacancy_stats_hh['average_salary'] = int(sum(all_pages_salaries) / len(all_pages_salaries))
    except ZeroDivisionError:
        vacancy_stats_hh['average_salary'] = None
    return vacancy_stats_hh


def get_page_rub_salary_sj(sj_page_payload):
    sj_page_salaries = []
    for vacancy in sj_page_payload['objects']:
        if vacancy['currency'] != 'rub':
            continue
        salary_from = vacancy['payment_from']
        salary_to = vacancy['payment_to']
        vacancy_average_salary = get_average_salary(salary_from, salary_to)
        if not vacancy_average_salary:
            continue
        sj_page_salaries.append(vacancy_average_salary)
    return sj_page_salaries


def predict_rub_salary_sj(sj_key, sj_area, vacancy, period):
    vacancies_url = 'https://api.superjob.ru/2.33/vacancies/'
    header = {'X-Api-App-Id': sj_key}
    params = {
        'keyword': vacancy,
        'town': sj_area,
        'payment_defined': True,
        'count': 100,
        'period': period
    }
    vacancies_found = 0
    vacancies_processed = 0
    all_pages_salaries = []
    for page in count(1):
        params['page'] = page
        page_response = requests.get(vacancies_url, headers=header, params=params)
        page_response.raise_for_status()
        page_payload = page_response.json()
        vacancies_found = page_payload.get('total')
        one_page_salaries = get_page_rub_salary_sj(page_payload)
        vacancies_processed += len(one_page_salaries)
        all_pages_salaries.extend(one_page_salaries)
        if not page_payload['more']:
            break
    vacancy_stats_sj = {
        'vacancies_found': vacancies_found,
        'vacancies_processed': vacancies_processed
    }
    try:
        vacancy_stats_sj['average_salary'] = int(sum(all_pages_salaries) / len(all_pages_salaries))
    except ZeroDivisionError:
        vacancy_stats_sj['average_salary'] = None
    return vacancy_stats_sj


def print_table(programming_languages, vacancy_stats, title):
    table = [
        [
            'Язык программирования',
            'Вакансий найдено',
            'Вакансий обработано',
            'Средняя зарплата'
        ]
    ]
    for programming_language in programming_languages:
        vacancy = f'Программист {programming_language}'
        vacancies_found = vacancy_stats[vacancy]['vacancies_found']
        vacancies_processed = vacancy_stats[vacancy]['vacancies_processed']
        average_salary = vacancy_stats[vacancy]['average_salary']
        row = [
            programming_language,
            vacancies_found,
            vacancies_processed,
            average_salary
        ]
        table.append(row)
    ascii_table = AsciiTable(table, title)
    print(ascii_table.table)


def main():
    load_dotenv()
    sj_key = os.environ['SUPER_JOB_SECRET_KEY']
    sj_area = {'Moscow': 4}
    hh_area = {'Moscow': 1}
    month = 30
    vacancy_stats_hh = {}
    vacancy_stats_sj = {}
    programming_languages = [
        'JavaScript',
        'Java',
        'Python',
        'Ruby',
        'PHP',
        'C++',
        'C#',
        'Go',
        '1C'
    ]
    for programming_language in programming_languages:
        vacancy = f'Программист {programming_language}'
        vacancy_stats_hh[vacancy] = predict_rub_salary_hh(vacancy, hh_area['Moscow'], period=month)
        vacancy_stats_sj[vacancy] = predict_rub_salary_sj(sj_key, sj_area['Moscow'], vacancy, month)
        print(f'Data for the vacancy "{vacancy}" is collected')
    print_table(programming_languages, vacancy_stats=vacancy_stats_hh, title=f'HeadHunter {list(hh_area)[0]}')
    print_table(programming_languages, vacancy_stats=vacancy_stats_sj, title=f'SuperJob {list(sj_area)[0]}')


if __name__ == '__main__':
    main()
