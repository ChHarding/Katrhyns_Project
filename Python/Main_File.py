import os
import pandas as pd
import matplotlib.pyplot as plt
#Copied and edited from HCI 574 lecture 36
from flask import Flask, render_template, request, redirect, url_for # now also import the render template class
app = Flask(__name__)


CSV_FILE = 'Transactions.csv'
INITIAL_BALANCE = 100.0


class AccountManager:
    def __init__(self,initial_balance = INITIAL_BALANCE,csv_file = CSV_FILE):
            self.csv_file = csv_file
            self.initial_balance = initial_balance
            self.df = self.load_file()


    def load_file(self):
            """Loads data from the CSV file"""
            if os.path.exists(self.csv_file):
                try:
                    df = pd.read_csv(self.csv_file)
                    print(f"File exists as {self.csv_file}")
                    return df
                except pd.errors.EmptyDataError:        #I did look this up on google but it seems to do what I'm wanting
                    print("Error: The file is empty.")
                    return None
            else:
                print(f"{self.csv_file} File not found")
                return None
            
    def __str__(self):
         s = (f"Database: {self.csv_file}, Initial Balance: {self.initial_balance}\n")
         if self.df is not None:
              s += ("DataFrame contents:\n")
              s += self.df.to_string()
              return s

    def update_balance(self):
        """Updates the current balance based on user activity, 
        after initial balance. Should update after loading"""
        current_balance = self.initial_balance
        #figure out how add the purhcase amount rows from CSV file
        for _, row in self.df.iterrows():
            if row['Type'] =='Purchase':
                current_balance -=row['Amount']
            elif row['Type'] =='Refund':
                current_balance += row['Amount']
        return current_balance

    def get_balance(self):
        """Gives user their current balance."""
        current_balance = self.initial_balance
        if not self.df.empty:
            purchases = self.df[self.df['Type'] == 'Purchase']['Amount'].sum()
            refunds = self.df[self.df['Type'] == 'Refund']['Amount'].sum()
            current_balance = self.initial_balance + purchases - refunds
        return current_balance

    def get_activity(self):
        """Gives user their activity."""
        return self.df.to_dict(orient='records')

    #The plot kept giving me so many errors, so I used google gemini to help me reformat the structure of plotting from your code
    #Before hand I was recieving so many errors for str being used instead of floats, and it caused the whole app to crash
    # I also added in the red line for the budget
    def plot(self, budget_amount = None):
        """Plots the balance over time."""
        if self.df is None or self.df.empty:
            print("DataFrame is empty, cannot plot.")
            # Ensure the static/plot.png file is cleared or a placeholder is shown if there's no data to plot.
            # Return None to indicate no plot was generated.
            # As a temporary workaround to avoid a broken image, creates an empty plot
            return 'static/no_data_plot.png' # Or some placeholder image

        #'Date' column is in datetime format for correct chronological plotting.
        try:
            self.df['Date'] = pd.to_datetime(self.df['Date'])
        except Exception as e:
            print(f"Error converting 'Date' column to datetime: {e}")
            # Handles cases where date conversion fails (e.g., malformed dates)
            return 'static/error_plot.png'

        # Sort by date to ensure the plot is chronological
        plot_df = self.df.sort_values(by='Date')

        # Add a new column for the balance change for each transaction
        # Purchase amounts are positive, Refunds are negative
        plot_df['Change'] = plot_df.apply(
            lambda row: +row['Amount'] if row['Type'] == 'Purchase' else row['Amount'],
            axis=1
        )
        #Calculate cumulative sum and add initial balance
        plot_df['Cumulative_Balance'] = self.initial_balance + plot_df['Change'].cumsum()
        
        # Now plot the Cumulative_Balance over the Date
        plt.figure(figsize=(10, 5))
        
        # Check if plot_df is empty after operations (e.g., if only header was present)
        if plot_df.empty:
            print("Plot DataFrame is empty after processing, cannot plot.")
            return 'static/no_data_plot.png' # Placeholder
        
        plt.plot(plot_df['Date'], plot_df['Cumulative_Balance'], marker='o', linestyle='-')
        plt.xlabel('Date')
        plt.ylabel('Balance ($)')
        
        #Red budget line
        if budget_amount is not None:
            plt.axhline(y=budget_amount, color='red', linestyle='--', label ='Budget')

        # Format x-axis for dates
        plt.gcf().autofmt_xdate() # Automatically format date labels
        
        plt.tight_layout()
        
        # Save the plot
        plot_path = 'static/plot.png'
        plt.savefig(plot_path)
        plt.close()
        
        return plot_path


accman = AccountManager()


@app.route("/")  
def index():
    current_balance = accman.get_balance()
    #Added things to get the budget number
    budget_amount_str = request.args.get('budget_amount')
    budget_amount = None
    if budget_amount_str:
        try:
            budget_amount = float(budget_amount_str)
        except ValueError:
            print("Invalid budget amount recieved")

    plot_path = accman.plot(budget_amount=budget_amount)
    transactions = accman.get_activity()
    html_str = render_template('index.html', title="Landing Page", plot_url=plot_path, balance=current_balance, transactions=transactions, budget_amount=budget_amount) # title will be inlined in {{ title }}
    print(html_str) # DEBUG
    return html_str  # give it to the browser to display the inline page

@app.route('/add_transaction', methods=['POST'])
def add_activity():
    """Adds new activity and will sort what type of activity it is(refund or charge),
    catagory(grocery/transportation), and the amount."""
    transaction_type = request.form['transaction_type']
    business_establishment = request.form['business_establishment']
    amount = request.form['amount']
    date = request.form['date']
    catagory = request.form['catagory']

    new_transaction = { # can be in any order but must match the Above CSV header
        'Type': transaction_type,
        'Business Establishment': business_establishment,
        'Amount': float(amount),
        'Date': date,  # BTW has different format that Date in csv file
        'Category': catagory 
    }   
    print(accman.df)
    # "add" new row at the bottom of the DataFrame
    accman.df = pd.concat([accman.df, pd.DataFrame([new_transaction])], ignore_index=True)
    print("\n\n", accman.df)
    # save the updated DataFrame to the CSV file
    accman.df.to_csv(accman.csv_file, index=False)

    # update the balance
    accman.update_balance()

    return redirect(url_for('index'))



app.run(debug=False, port=8080) 
