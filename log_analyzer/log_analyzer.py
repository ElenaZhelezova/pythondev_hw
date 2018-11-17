#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os
import io
import re
from datetime import datetime
import collections
import logging
import gzip
from string import Template
import json


latest_log = collections.namedtuple('latest_log', ['log_file_date', 'log_file_name'])
report_template = 'report.html'
config_pattern = r'[\"\'](?P<c_name>\S+)[\"\']: (?P<c_value>\S+)$'
log_file_pattern = r'^nginx-access-ui\.log-(?P<date>\d{8})(\.gz)?$'
parse_line_pattern = re.compile(r'^\S+ '                          # remote_addr
                              '\S+  '                             # remote_user
                              '\S+ '                              # http_x_real_ip
                              '\[\S+ \S+\] '                      # time_local
                              '\"\S+ (?P<url_name>\S+) \S+\" '    # request
                              '\S+ '                              # status
                              '\S+ '                              # body_bites_sent
                              '\"\S+\" '                          # http_referer
                              '\".*\" '                           # http_user_agent
                              '\"\S+\" '                          # http_x_forwarded_for
                              '\"\S+\" '                          # http_X_REQUEST_ID
                              '\"\S+\" '                          # http_X_RB_USER
                              '(?P<request_time>\d+\.\d+)$'       # request_time
                              )


def get_config(file_path=None):
    """
    parsing config parameters from config file
    :param config file path
    :return config parameters
    """
    default_config = {
        "REPORT_SIZE": 1000,
        "REPORT_DIR": "./reports",
        "LOG_DIR": "./log"
    }
    if file_path is None:
        return default_config

    if not os.path.exists(file_path):
        return IOError

    with open(file_path, 'rb') as f:
        file_conf = json.load(f, encoding='utf-8')

    if not file_conf:
        return ValueError

    default_config.update(file_conf)

    return default_config


def create_logging(logging_dir=''):
    """
    creating monitoring of a script working
    :param logging_dir - dir, where logging write to
    :return:
    """
    if os.path.isdir(logging_dir):
        logging_file = os.path.join(logging_dir, 'log_analyze.log')
    else:
        logging_file = None

    logging.basicConfig(filename=logging_file, format='[%(asctime)s] %(levelname).1s %(message)s',
                        datefmt='%Y.%m.%d %H:%M:%S', level=logging.INFO)
    logging.info('logging has been started')


def get_log(log_dir):
    """
    finding the latest nginx log file to analyze
    :param log_dir:
    :return log file's name
    """
    if not os.path.isdir(log_dir):
        return None

    latest_log_file = None
    for file_name in os.listdir(log_dir):
        file_name.decode('utf-8')
        match_file = re.match(log_file_pattern, file_name)
        if not match_file:
            continue

        date_string = match_file.groupdict()['date']

        try:
            file_date = datetime.strptime(date_string, "%Y%m%d").date()
        except ValueError:
            continue

        if not latest_log_file or file_date > latest_log_file.log_file_date:
            latest_log_file = latest_log(log_file_date=file_date, log_file_name=file_name)
    logging.info('latest log file has been found')
    return latest_log_file


def create_report(file_path, report_size, max_err_perc=60):
    """

    :param file_path:
    :param report_size:
    :param max_err_perc:
    :return:
    """
    records = read_log_file(file_path, max_err_perc)
    total_requests = 0
    total_requests_time = 0
    report_dict = {}
    for i in records:
        total_requests += 1
        total_requests_time += round(float(i[1]), 4)
        report_dict = create_report_dict(i[0], round(float(i[1]), 4), report_dict)
    sort_report_list = (sorted(report_dict.itervalues(), key=lambda report_dict: report_dict['time_sum'], reverse=True))
    sort_report_list = sort_report_list[:report_size]
    finally_list = update_report_list(sort_report_list, total_requests, total_requests_time)
    return finally_list


def read_log_file(file_path, max_err_perc):
    """
    reading log file and count parsing errors
    :param file_path:
    :return: parsed args from lines
    """
    log = gzip.open if file_path.endswith('.gz') else io.open

    total_lines = parsed = 0
    with log(file_path, 'rb') as lf:
        for line in lf:
            record_line = parse_line(line.decode('utf-8'))
            total_lines += 1
            if record_line:
                parsed += 1
                yield record_line
            else:
                logging.info('line has not been parsed')

    error_perc = ((total_lines-parsed)/total_lines)*100
    if error_perc >= max_err_perc:
        logging.exception('the number of errors exceeded the allowed')
    else:
        logging.info('{}% of lines has not been parsed'.format(error_perc))


def parse_line(record):
    """
    parsing line, get url name and request time
    :param record:
    :return: url, request time of it
    """
    match_line = parse_line_pattern.match(record)
    url_name = match_line.groupdict()['url_name']
    request_time = match_line.groupdict()['request_time']
    return url_name, request_time


def create_report_dict(arg1, arg2, dict_in):
    """
    creating dictionary with info, about how often did it found, sum of request time of it, average time and
    creating list of request times
    :param arg1:
    :param arg2:
    :param dict_in:
    :return: dictionary  {{url, count, time_sum, time_avg, [request time]}}
    """
    if arg1 in dict_in:
        dict_in[arg1]['count'] += 1
        dict_in[arg1]['time_sum'] += arg2
        dict_in[arg1]['time_avg'] = round((dict_in[arg1]['time_sum'])/(dict_in[arg1]['count']), 3)
        dict_in[arg1]['time_list'].append(arg2)
    else:
        dict_in[arg1] = {'url': arg1,
                         'count': 1,
                         'time_sum': arg2,
                         'time_avg': arg2,
                         'time_list': [arg2]}
    return dict_in


def update_report_list(list_in, total_request, total_time):
    """
    updating url's info dictionary with max request time, median time, count percent and request time percent
    :param list_in:
    :param total_request:
    :param total_time:
    :return:
    """
    for i in list_in:
        time_list = i['time_list']
        time_list.sort()
        i['time_max'] = time_list[-1]
        i['time_med'] = round(get_median(time_list), 3)
        i['count_perc'] = round((float(i['count'])/total_request)*100, 3)
        i['time_perc'] = round((i['time_sum']/total_time)*100, 3)
        del(i['time_list'])
    return list_in


def get_median(list_in):
    """
    counting median of list values
    :param list_in:
    :return: median
    """
    if len(list_in)%2 == 1 and len(list_in) > 1:
        mediana = list_in[(len(list_in)//2)]
    elif len(list_in)%2 == 0 and len(list_in) > 1:
        mediana = (list_in[(len(list_in)/2)-1]+list_in[(len(list_in)/2)])/2
    else: mediana = list_in[0]
    return mediana


def render_report(template_file, report_path, data):
    """
    rendering report of nginx log analyzing
    :param template_file:
    :param report_path:
    :param data:
    :return:
    """
    report_dir = os.path.dirname(report_path)
    if not report_dir:
        os.makedirs(report_dir)
        logging.info('report dir has been created')

    with open(template_file) as t_file:
        template_str = t_file.read().decode('utf-8')
        template = Template(template_str)

    rendering_report = template.safe_substitute(table_json=json.dumps(data))

    with open(report_path, 'w') as rp:
        rp.write(rendering_report)


def main(config):
    analyzing_log = get_log(config.get('LOG_DIR'))
    if not analyzing_log:
        logging.info('No log file to analyze')
        return

    report_name = 'report-{}.html'.format(analyzing_log.log_file_date.strftime('%Y.%m.%d'))
    report_file_path = os.path.join(config.get('REPORT_DIR'), report_name)

    if os.path.isfile(report_file_path):
        logging.info('Nothing to analyze')
        return

    new_report = create_report(analyzing_log.log_file_name, int(config.get('REPORT_SIZE')), int(config.get('MAX_ERR_PERC', 60)))
    logging.info('new report has been created')
    render_report(report_template, report_file_path, new_report)
    logging.info('report has been rendered')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='default_config.conf')
    args = parser.parse_args()

    try:
        config = get_config(args.config)
    except ValueError, IOError:
        raise SystemExit('config file does not exist')

    create_logging(config.get('LOGGING_DIR'))

    try:
        main(config)
    except:
        logging.exception('something went wrong', exc_info=True)
