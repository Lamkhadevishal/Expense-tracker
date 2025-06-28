from flask import Flask, render_template, request, redirect, url_for,flash
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
import json
from datetime import datetime
from constant import *

app = Flask(__name__)
DATA_FILE = DATA_FILE
BUDGET_FILE = BUDGET_FILE

def set_budget(amount):
    with open(BUDGET_FILE, 'w') as f:
        f.write(str(amount))

def get_budget():
    if os.path.exists(BUDGET_FILE):
        with open(BUDGET_FILE, 'r') as f:
            content = f.read().strip()
            if content:
                return float(content)
    return 0.0



def load_expenses_from_excel():
    if os.path.exists(DATA_FILE):
        df = pd.read_excel(DATA_FILE, engine="openpyxl")
        # print("Columns loaded:", df.columns.tolist())
        df.columns = df.columns.astype(str).str.lower()
        # Reorder and rename all columns explicitly before saving
        

        return df
    return pd.DataFrame(columns=['id', 'date', 'name', 'category', 'amount', 'description'])

@app.route('/')
def homepage():
    df = load_expenses_from_excel()
    expenses = df.to_dict(orient='records')
    generate_charts(expenses)
    total_balance = sum(float(e['amount']) for e in expenses)
    return render_template('index.html', total_balance=total_balance)

@app.route('/post')
def transaction():
    df = load_expenses_from_excel()
    print("Data for Transaction Route:\n", df.head())
    print("Columns in Transaction Route:", df.columns.tolist())
    expenses = df.to_dict(orient='records')
    message = request.args.get('message', '')
    return render_template('expenses.html', expenses=expenses, message=message)
@app.route('/add', methods=['POST'])
def add_expense():
    df = load_expenses_from_excel()
    date = request.form.get('date')
    name = request.form.get('name')
    category = request.form.get('category')
    if category:
        category = category.strip().title()
    amount = request.form.get('amount')
    description = request.form.get('description', 'No description provided')

    if not date or not name or not category:
        return render_template('expenses.html',
                               expenses=df.to_dict(orient='records'),
                               message='❌ All fields except description are required.')

    try:
        amount = float(amount)
    except ValueError:
        return render_template('expenses.html',
                               expenses=df.to_dict(orient='records'),
                               message='❌ Please enter a valid amount.')

    # Load existing budget
    budget = get_budget()  # Make sure you have this function defined

    # Calculate total spent so far (before adding new expense)
    total_spent = df['amount'].sum()

    # Check if adding this entry will exceed budget
    if budget and (total_spent + amount) > budget:
        return render_template('expenses.html',
                               expenses=df.to_dict(orient='records'),
                               message="🚨 Don't purchase more! You are out of limit.")

    # Add the new entry
    new_id = df['id'].max() + 1 if not df.empty else 1
    new_entry = pd.DataFrame([{
        'id': new_id,
        'date': date,
        'name': name,
        'category': category,
        'amount': amount,
        'description': description
    }])

    df = pd.concat([df, new_entry], ignore_index=True)
    df = df[['id', 'date', 'name', 'category', 'amount', 'description']]
    df.to_excel(DATA_FILE, index=False, engine='openpyxl')

    return redirect(url_for('transaction'))



@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_expense(id):
    df = load_expenses_from_excel()
    if request.method == 'POST':
        df.loc[df['id'] == id, ['date', 'category', 'description', 'amount']] = [
            request.form['date'], request.form['category'], request.form['description'], request.form['amount']
        ]
        df.to_excel(DATA_FILE, engine="openpyxl", index=False)
        return redirect(url_for('transaction'))
    else:
        expense = df.loc[df['id'] == id].to_dict('records')[0]
        return render_template('edit_expense.html', expense=expense)

@app.route('/delete/<int:id>', methods=['POST'])
def delete_expense(id):
    df = load_expenses_from_excel()
    df = df[df['id'] != id]
    df.to_excel(DATA_FILE, engine="openpyxl", index=False)
    # flash('✅ One item deleted')
    return redirect(url_for('transaction', message="✅ Item deleted successfully"))
@app.route('/budget')
def budget_page():
    df = load_expenses_from_excel()
    expenses = df.to_dict(orient='records')
    total_spent = sum(float(e['amount']) for e in expenses)
    budget = get_budget()
    balance = budget - total_spent
    return render_template(
        'budget.html',
        budget=budget,
        balance=balance,
        expenses=expenses,
        message=""
    )
    
@app.route('/set_budget', methods=['POST'])
def set_budget_route():
    amount = request.form.get('budget')
    print(amount)

    # FIX: Check if it's None or an empty string
    if not amount:
        df = load_expenses_from_excel()
        
        expenses = df.to_dict(orient='records')
        total_spent = sum(float(e['amount']) for e in expenses)
        return render_template(
            'budget.html',
            budget=get_budget(),
            balance=get_budget() - total_spent,
            expenses=expenses,
            message="❌ Budget amount cannot be empty."
        )

    try:
        amount = float(amount)
        set_budget(amount)
        return redirect(url_for('budget_page'))
    except ValueError:
        df = load_expenses_from_excel()
        expenses = df.to_dict(orient='records')
        total_spent = sum(float(e['amount']) for e in expenses)
        return render_template(
            'budget.html',
            budget=get_budget(),
            balance=get_budget() - total_spent,
            expenses=expenses,
            message="❌ Invalid budget amount."
        )


def generate_charts(expenses):
    os.makedirs("static/images", exist_ok=True)
    df = pd.DataFrame(expenses)

    if df.empty:
        return

    df.columns = df.columns.astype(str).str.lower()
    df['date'] = pd.to_datetime(df['date'])

    # Donut Chart
    plt.figure(figsize=(5, 5))
    df.groupby('category')['amount'].sum().plot.pie(
        autopct='%1.1f%%', startangle=90, wedgeprops=dict(width=0.4))
    plt.title('Expenses by Category')
    plt.ylabel('')
    plt.tight_layout()
    plt.savefig('static/images/donut.png')
    plt.close()

    # Line Chart
    df_sorted = df.sort_values('date')
    df_sorted['cumulative'] = df_sorted['amount'].cumsum()
    plt.figure(figsize=(7, 4))
    plt.plot(df_sorted['date'], df_sorted['cumulative'], marker='o', linestyle='-', color='green')
    plt.title('Cumulative Expenses Over Time')
    plt.xlabel('Date')
    plt.ylabel('Total Spent (₹)')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('static/images/line.png')
    plt.close()

    # Bar Chart
    recent = df[df['date'] >= df['date'].max() - pd.Timedelta(days=6)]
    bar_data = recent.groupby(recent['date'].dt.strftime('%b %d'))['amount'].sum()
    plt.figure(figsize=(7, 4))
    bar_data.plot(kind='bar', color='skyblue')
    plt.title('Expenses in Last 7 Days')
    plt.xticks(rotation=45)
    plt.ylabel('₹')
    plt.tight_layout()
    plt.savefig('static/images/bar.png')
    plt.close()

if __name__ == '__main__':
    app.run(debug=True)
