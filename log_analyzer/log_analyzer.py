#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os
import re
from datetime import datetime
import collections
import logging
import gzip
from string import Template
import json


def get_config(file_path):
    """
    parsing config parameters from config file
    :param config file path
    :return config parameters
    """
    if os.path.exists(file_path):
        with open(file_path, 'rb') as f:
            file_list = f.readlines()
            file_conf = {}
            for i in file_list:
                i.decode('utf-8')
                match_line = re.match('[\"\'](?P<c_name>\S+)[\"\']: (?P<c_value>\S+)$', i)
                if match_line:
                    c_name = match_line.groupdict()['c_name']
                    c_value = match_line.groupdict()['c_value']
                    file_conf[c_name] = c_value.strip("\",")

        return file_conf


def create_monitoring(monitoring_dir=''):
    """
    creating monitoring of a programm working
    :param dir, where logging write to
    :return:
    """
    if os.path.isdir(monitoring_dir):
        monitoring_file = os.path.join(monitoring_dir, 'log_analyze_monitoring.log')
    else:
        monitoring_file = None

    logging.basicConfig(filename=monitoring_file, format='[%(asctime)s] %(levelname).1s %(message)s',
                        datefmt='%Y.%m.%d %H:%M:%S', level=logging.INFO)
    logging.info('monitoring has been started')


def get_log(log_dir):
    """
    finding the latest nginx log file to analyze
    :param log_dir:
    :return log file's name
    """
    if os.path.isdir(log_dir):
        latest_log = collections.namedtuple('latest_log', ['log_file_date', 'log_file_name'])
        latest_log_file = None
        for file_name in os.listdir(log_dir):
            file_name.decode('utf-8')
            match_file = re.match('^nginx-access-ui\.log-(?P<date>\d{8})(\.gz)?$', file_name)
            if match_file:
                date_string = match_file.groupdict()['date']
                file_date = datetime.strptime(date_string, "%Y%m%d").date()

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
    records = list(read_log_file(file_path, max_err_perc))
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
    if file_path.endswith('.gz'):
        log = gzip.open(file_path, 'rb')
    else:
        log = open(file_path)
    total_lines = parsed = 0
    for line in log:
        record_line = parse_line(line.decode('utf-8'))
        total_lines += 1
        if record_line:
            parsed += 1
            yield record_line
        else:
            logging.info('line has not been parsed')
    log.close()
    error_perc = ((total_lines-parsed)/total_lines)*100
    if error_perc >= max_err_perc:
        logging.exception('the number of errors exceeded the allowed')
        raise SyntaxError
    else:
        logging.info('{}% of lines has not been parsed'.format(error_perc))


def parse_line(record):
    """
    parsing line, get url name and request time
    :param record:
    :return: url, request time of it
    """
    find_in_line = re.compile('^\S+ '                             # remote_addr
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
    match_line = find_in_line.match(record)
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
    countig median of list values
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
        template_str = t_file.read().encode('utf-8')
        template = Template(template_str)

    rendering_report = template.safe_substitute(table_json=json.dumps(data))

    with open(report_path, 'w') as rp:
        rp.write(rendering_report)


def main(config):
    log_file_name = get_log(config.get('LOG_DIR'))
    actual_date = log_file_name.log_file_date
    log_file = log_file_name.log_file_name

    report_name = 'report-{}.html'.format(actual_date)
    report_file_path = os.path.join(config.get('REPORT_DIR'), report_name)
    report_template = 'report.html'
    if not os.path.isfile(report_file_path):
        new_report = create_report(log_file, int(config.get('REPORT_SIZE')), int(config.get('MAX_ERR_PERC', 60)))
        logging.info('new report has been created')
        render_report(report_template, report_file_path, new_report)
        logging.info('report has been rendered')
    else:
        logging.info('Nothing to analyze')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='default_config.conf')
    args = parser.parse_args()

    config = {
        "REPORT_SIZE": 1000,
        "REPORT_DIR": "./reports",
        "LOG_DIR": "./log"
    }

    if args.config:
        try:
            new_config = get_config(args.config)
            config.update(new_config)
        except TypeError:
            raise SystemExit('config file does not exist')

    if config.get('MONITORING_DIR'):
        create_monitoring(config.get('MONITORING_DIR'))
    else:
        create_monitoring('')

    try:
        main(config)
    except:
        logging.exception('something went wrong', exc_info=True)
