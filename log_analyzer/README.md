<h2>log_analyzer.py</h2>
<p>Скрпт анализирует лог-файл веб-интерфейса с самой свежей датой в <b>LOG_DIR</b>, и формирует отчет из <b>REPORT_SIZE</b> URL’ов, отсортированных по максимальному суммарному времени обработки запроса.<p>
<br>
<div><p>Скрипту возможно указать считать конфиг из файла, передав его путь через <em>--config</em>:</p>  
<p><em> >>> $ python log_analyzer.py --config <путь_до_файла> </em></p>  
<br>
<h4>Конфиг по умолчанию:</h4>
<div>
<p><b>“REPORT_SIZE”: 1000</b> &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; количество строк в отчете</p>
<p><b>“REPORT_DIR”: “./reports”</b> &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; директория с готовыми отчетами</p>
<p><b>“LOG_DIR”: “./log”</b> &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; директория с логами</p>
<p><b>“MONITORING_DIR”: “None”</b> &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; путь до лог-файла скрипта</p>
<p><b>“MAX_ERR_PERC”: “60”</b> &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; допустимое количество ошибок при обработке файла</p>
</div>
<br>
<h4>Запуск тестов (unittest):</h4>
<p><em> >>> $ python -m unittest test_log_analyzer </em></p>
