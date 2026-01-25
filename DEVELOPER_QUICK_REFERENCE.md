# Developer Quick Reference - WMS Modules

## 🚀 Quick Start

### Adding a New Module

1. **Create Module Structure**
```bash
mkdir modules/<module_name>
touch modules/<module_name>/__init__.py
touch modules/<module_name>/models.py
touch modules/<module_name>/routes.py
```

2. **Define Models** (`models.py`)
```python
from app import db
from datetime import datetime

class MyModel(db.Model):
    __tablename__ = 'my_table'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

3. **Create Migration** (`migrations/add_<module_name>_module.py`)
```python
from app import app, db
from modules.<module_name>.models import MyModel

def create_tables():
    with app.app_context():
        db.create_all()
        print("✅ Tables created")

if __name__ == '__main__':
    create_tables()
```

4. **Create Routes** (`routes.py`)
```python
from flask import Blueprint, jsonify
from flask_login import login_required

bp = Blueprint('<module_name>', __name__, url_prefix='/<module_name>')

@bp.route('/api/endpoint', methods=['GET'])
@login_required
def endpoint():
    return jsonify({'success': True})
```

5. **Register Blueprint** (`main.py`)
```python
from modules.<module_name>.routes import bp
app.register_blueprint(bp)
```

6. **Update Consolidated Migration**
```python
# In mysql_consolidated_migration_v2.py
from modules.<module_name>.models import MyModel
```

---

## 📊 Database Models Reference

### Common Fields

```python
# Primary Key
id = db.Column(db.Integer, primary_key=True)

# Timestamps
created_at = db.Column(db.DateTime, default=datetime.utcnow)
updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Foreign Keys
user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

# Relationships
items = db.relationship('Item', backref='parent', lazy=True, cascade='all, delete-orphan')
```

### Common Data Types

```python
db.String(255)          # VARCHAR
db.Integer              # INT
db.Float                # FLOAT
db.Boolean              # BOOLEAN
db.Date                 # DATE
db.DateTime             # DATETIME
db.Text                 # TEXT
db.JSON                 # JSON
```

---

## 🔌 API Endpoints Pattern

### Standard CRUD Operations

```python
# GET - List all
@bp.route('/api/items', methods=['GET'])
@login_required
def list_items():
    items = Item.query.all()
    return jsonify({'success': True, 'items': [...]})

# GET - Get one
@bp.route('/api/items/<int:item_id>', methods=['GET'])
@login_required
def get_item(item_id):
    item = Item.query.get(item_id)
    return jsonify({'success': True, 'item': {...}})

# POST - Create
@bp.route('/api/items', methods=['POST'])
@login_required
def create_item():
    data = request.get_json()
    item = Item(**data)
    db.session.add(item)
    db.session.commit()
    return jsonify({'success': True, 'id': item.id})

# PUT - Update
@bp.route('/api/items/<int:item_id>', methods=['PUT'])
@login_required
def update_item(item_id):
    item = Item.query.get(item_id)
    data = request.get_json()
    for key, value in data.items():
        setattr(item, key, value)
    db.session.commit()
    return jsonify({'success': True})

# DELETE - Delete
@bp.route('/api/items/<int:item_id>', methods=['DELETE'])
@login_required
def delete_item(item_id):
    item = Item.query.get(item_id)
    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True})
```

---

## 🔐 Security Best Practices

### Authentication
```python
from flask_login import login_required, current_user

@bp.route('/api/protected', methods=['GET'])
@login_required
def protected():
    user_id = current_user.id
    return jsonify({'user': user_id})
```

### Authorization
```python
@bp.route('/api/admin-only', methods=['GET'])
@login_required
def admin_only():
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    return jsonify({'success': True})
```

### Input Validation
```python
@bp.route('/api/create', methods=['POST'])
@login_required
def create():
    data = request.get_json()
    
    # Validate required fields
    required = ['name', 'email']
    if not all(field in data for field in required):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Validate data types
    if not isinstance(data['name'], str):
        return jsonify({'error': 'Invalid data type'}), 400
    
    return jsonify({'success': True})
```

---

## 🗄️ Database Operations

### Query Examples

```python
# Get all
items = Item.query.all()

# Get one by ID
item = Item.query.get(1)

# Get one by filter
item = Item.query.filter_by(name='Test').first()

# Get multiple by filter
items = Item.query.filter_by(status='active').all()

# Complex filter
items = Item.query.filter(
    Item.status == 'active',
    Item.created_at > datetime(2026, 1, 1)
).all()

# Count
count = Item.query.count()

# Order by
items = Item.query.order_by(Item.created_at.desc()).all()

# Limit and offset
items = Item.query.limit(10).offset(20).all()

# Join
items = db.session.query(Item, User).join(User).all()
```

### Create/Update/Delete

```python
# Create
item = Item(name='Test', status='active')
db.session.add(item)
db.session.commit()

# Update
item = Item.query.get(1)
item.name = 'Updated'
db.session.commit()

# Delete
item = Item.query.get(1)
db.session.delete(item)
db.session.commit()

# Bulk operations
items = [Item(name=f'Item {i}') for i in range(10)]
db.session.add_all(items)
db.session.commit()
```

### Error Handling

```python
try:
    item = Item(name='Test')
    db.session.add(item)
    db.session.commit()
except Exception as e:
    db.session.rollback()
    logger.error(f"Error: {str(e)}")
    return jsonify({'error': str(e)}), 500
```

---

## 📝 Logging

### Setup
```python
import logging

logger = logging.getLogger(__name__)

# Log levels
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
logger.critical("Critical message")
```

### Best Practices
```python
# Log important operations
logger.info(f"User {user_id} created item {item_id}")

# Log errors with context
logger.error(f"Failed to create item: {str(e)}", exc_info=True)

# Log SAP B1 interactions
logger.info(f"SAP B1 API call: {endpoint}")
logger.debug(f"SAP B1 Response: {response}")
```

---

## 🧪 Testing

### Unit Test Template
```python
import unittest
from app import app, db

class TestMyModule(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.app = app.test_client()
        with app.app_context():
            db.create_all()
    
    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_endpoint(self):
        response = self.app.get('/api/endpoint')
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()
```

---

## 📦 Module Structure

### Recommended Layout
```
modules/
├── grpo/
│   ├── __init__.py
│   ├── models.py
│   ├── routes.py
│   ├── templates/
│   │   └── grpo/
│   │       ├── index.html
│   │       └── detail.html
│   └── static/
│       └── js/
│           └── grpo.js
├── grpo_transfer/
│   ├── __init__.py
│   ├── models.py
│   ├── routes.py
│   └── templates/
│       └── grpo_transfer/
│           └── index.html
└── multi_grn_creation/
    ├── __init__.py
    ├── models.py
    ├── routes.py
    └── templates/
        └── multi_grn/
            └── index.html
```

---

## 🔄 SAP B1 Integration

### API Call Pattern
```python
from sap_integration import SAPIntegration

sap = SAPIntegration()

# SQL Query
response = sap.call_sap_api(
    method='POST',
    endpoint="SQLQueries('QueryName')/List",
    data={'ParamList': "param='value'"}
)

# OData
response = sap.call_sap_api(
    method='GET',
    endpoint="Items?$select=ItemCode,ItemName",
    headers={'Prefer': 'odata.maxpagesize=0'}
)

# Create/Update
response = sap.call_sap_api(
    method='POST',
    endpoint='StockTransfers',
    data={...}
)
```

---

## 📋 Checklist for New Module

- [ ] Create module directory structure
- [ ] Define database models
- [ ] Create migration file
- [ ] Create API routes
- [ ] Register blueprint in main.py
- [ ] Update consolidated migration
- [ ] Create module documentation
- [ ] Add to MIGRATION_TRACKING.md
- [ ] Test all endpoints
- [ ] Add error handling
- [ ] Add logging
- [ ] Add security checks
- [ ] Create unit tests
- [ ] Update this reference

---

## 🆘 Common Issues & Solutions

### Issue: Import Error
```python
# ❌ Wrong
from models import User

# ✅ Correct
from models import User  # If in root
from app.models import User  # If in package
```

### Issue: Database Not Updating
```python
# ❌ Forgot to commit
db.session.add(item)

# ✅ Correct
db.session.add(item)
db.session.commit()
```

### Issue: Foreign Key Error
```python
# ❌ Wrong - user doesn't exist
item = Item(user_id=999)
db.session.add(item)
db.session.commit()

# ✅ Correct - verify user exists
user = User.query.get(1)
if user:
    item = Item(user_id=user.id)
    db.session.add(item)
    db.session.commit()
```

### Issue: Circular Import
```python
# ❌ Wrong - circular dependency
# models.py imports routes
# routes.py imports models

# ✅ Correct - import at function level
def my_function():
    from models import User
    return User.query.all()
```

---

## 📚 Resources

- **Flask Documentation:** https://flask.palletsprojects.com/
- **SQLAlchemy Documentation:** https://docs.sqlalchemy.org/
- **SAP B1 API:** https://help.sap.com/docs/SAP_BUSINESS_ONE
- **Project Documentation:** See module guide files

---

## 📞 Support

For questions or issues:
1. Check module documentation
2. Review similar modules
3. Check application logs
4. Contact development team