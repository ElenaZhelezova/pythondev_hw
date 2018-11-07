<h2>log analyzer.py</h2>
Скрпт анализирует лог-файл веб-интерфейса с самой свежей датой в **LOG_DIR**, и формирует отчет из **REPORT_SIZE** URL’ов, отсортированных по максимальному суммарному времени обработки запроса.
<br>
Скрипту возможно указать считать конфиг из файла, передав его путь через _--config_:  
> ```$ python log_analyzer.py –config <путь_до_файла>```  

<br>
<h4>Конфиг по умолчанию:</h4>
<dt>“REPORT_SIZE”: 1000</dt> <dd> *количество строк в отчете* </dd><dt>“REPORT_DIR”: “./reports”</dt> <dd> *директория с готовыми отчетами* <dd><dt>“LOG_DIR”: “./log”</dt> <dd> *директория с логами* </dd>
<dt>“MONITORING_DIR”: “None”</dt><dd> *путь до лог-файла скрипта* </dd><dt>“MAX_ERR_PERC”: “60”</dt> <dd> *допустимое количество ошибок при обработке файла*</dd>
<br>
<h4>Запуск тестов (unittest):</h4>
> ```$ python -m unittest test_log_analyzer```