import pandas as pd
from faker import Faker
import random
import csv


fake = Faker()

# ── 1. CUSTOMERS ──────────────────────────────────────────
customers = []
for i in range(1, 1001):
    customers.append({
        "customer_id": i,
        "name":        fake.name(),
        "email":       fake.email(),
        "city":        fake.city(),
        "created_at":  fake.date_between(start_date="-3y", end_date="today").isoformat(),
    })

# ── 2. PRODUCTS ───────────────────────────────────────────
categories = ["Electronics", "Clothing", "Food", "Books", "Sports"]

products = []
for i in range(1, 201):
    products.append({
        "product_id": i,
        "name":       fake.word().capitalize() + " " + fake.word().capitalize(),
        "category":   random.choice(categories),
        "price":      round(random.uniform(1.99, 999.99), 2),
    })

# ── 3. ORDERS (czyste) ────────────────────────────────────
customer_ids = [c["customer_id"] for c in customers]
product_ids  = [p["product_id"]  for p in products]

orders = []
for i in range(1, 50001):
    orders.append({
        "order_id":    i,
        "customer_id": random.choice(customer_ids),  # tylko istniejące
        "product_id":  random.choice(product_ids),   # tylko istniejące
        "quantity":    random.randint(1, 10),
        "amount":      round(random.uniform(5.0, 2000.0), 2),
        "order_date":  fake.date_between(start_date="-2y", end_date="today").isoformat(),
        "status":      random.choice(["pending", "paid", "cancelled", "refunded"]),
    })

# ── 4. CELOWE BŁĘDY ───────────────────────────────────────

# 5% duplikatów — losowe zamówienia skopiowane ponownie
duplicates = random.sample(orders, k=int(len(orders) * 0.05))
orders.extend(duplicates)

# 3% brakujących wartości — wyzeruj losowe pola
for order in random.sample(orders, k=int(len(orders) * 0.03)):
    field = random.choice(["customer_id", "amount", "status"])
    order[field] = None

# 2% złych dat — format nie do sparsowania
for order in random.sample(orders, k=int(len(orders) * 0.02)):
    order["order_date"] = random.choice([
        "15/03/2024",    # zły format
        "not-a-date",    # śmieć
        "2024-13-01",    # nieistniejący miesiąc
    ])

random.shuffle(orders)  # wymieszaj żeby błędy nie były na końcu

# ── 5. ZAPIS DO CSV ───────────────────────────────────────
def write_csv(filename, rows, fieldnames):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

write_csv("customers.csv", customers,
          ["customer_id", "name", "email", "city", "created_at"])

write_csv("products.csv", products,
          ["product_id", "name", "category", "price"])

write_csv("orders.csv", orders,
          ["order_id", "customer_id", "product_id", "quantity", "amount", "order_date", "status"])

print(f"customers : {len(customers)}")
print(f"products  : {len(products)}")
print(f"orders    : {len(orders)} (w tym ~2500 duplikatów, ~1500 braków, ~1000 złych dat)")