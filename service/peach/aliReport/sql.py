# service/peach/aliReport/sql.py
"""
阿里报告相关的SQL语句
"""

ALI_REPORT_SQL = {
    'insert': (
        'INSERT INTO ali_rp_check (pharmacist, patientSex, patientAge, primaryDiagnosis, '
        'medicines, pass, reason, query, rpID, refuse) '
        'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'
    ),
}


