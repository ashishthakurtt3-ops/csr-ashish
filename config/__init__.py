"""Django project package.

Registers PyMySQL as the MySQLdb driver so Django's MySQL backend can
use the pure-Python connector (no compiler/system libs required).
"""

import pymysql

# Django gates the MySQL backend on a MySQLdb >= 1.4 identity; report
# that version so PyMySQL satisfies the check.
pymysql.version_info = (1, 4, 6, "final", 0)
pymysql.install_as_MySQLdb()
