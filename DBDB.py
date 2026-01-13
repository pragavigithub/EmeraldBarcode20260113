import pyodbc
SERVER = "192.168.0.169,1433"
DATABASE = "EINV-TESTDB-LIVE-HUST"
USERNAME = "remoteuser"
PASSWORD = "Ea@12345"
try:
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        f"UID={USERNAME};"
        f"PWD={PASSWORD};"
        "TrustServerCertificate=yes;"
    )
    print("✅ SQL Server Connected Successfully")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ItemCode, ItemName, OnHand, InvntryUom
        FROM OITM Where OnHand > 0
    """)
    rows = cursor.fetchall()
    for r in rows:
        print(f"Item:-> {r.ItemCode} | ItemDesc:->{r.ItemName} | Stock :-> {r.OnHand} {r.InvntryUom}")
    conn.close()
except Exception as e:
    print("❌ Connection Failed:", e)
