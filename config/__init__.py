# PyMySQL fallback — only used if mysqlclient is unavailable.
# To use it: pip install pymysql cryptography
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    pass