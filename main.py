# importing required modules
import PyPDF2
import numpy as np
import re
import datetime
import pandas as pd
import os

def get_index(firstIndex,string):
    return int(firstIndex)+int(len(string))

def get_new_PL(disposable):
    # EMI = P x R x (1+R)^N / [(1+R)^N-1] (where n = 60 months, r = 15% per annum and EMI = disposable)
    # disp = prq
    # q = a/b
    # a = (1 + (0.15/12))**60
    var1 = 1 + (0.15/12)
    var2 = 0.15/12
    var3 = var1**60
    
    value1 = (var3 - 1)*disposable
    value2 = var2*var3
    principal_amt = value1/value2
    return principal_amt

def get_top_up(df:pd.DataFrame):
    top_up_label = list()
    try:
        top_up = df.loc["3_PersonalLoan"]["Paid Principle"]
        top_up_label = ["Personal Loan",top_up]
    except KeyError:
        pass
    try:
        top_up = df.loc["5_AutoLoan"]["Paid Principle"]
        top_up_label = ["Auto Loan",top_up]
    except KeyError:
        pass
    try:
        top_up = df.loc["6_HomeLoan"]["Paid Principle"]
        top_up_label = ["Home Loan",top_up] 
    except KeyError:
        pass
    return top_up_label


def diff_month(d1, d2):
    try:
        return (d1.year - d2.year) * 12 + d1.month - d2.month
    except AttributeError:
        return 0

def save_as_csv(data_df,pivot_df,csv,filename,info_df,rec_df,filePath):
    # remove date_opened,foir,disposable,salary
    data_df = data_df.drop(columns=['date_opened','Foir','Disposable','salary'])
    if(csv):
        try:
            os.mkdir(f'{filePath}/csv/{filename}')
        except FileExistsError:
            pass
        data_df.to_csv(f'{filePath}/csv/{filename}/{filename}_CAR_1.csv',index=False)
        pivot_df.to_csv(f'{filePath}/csv/{filename}/{filename}_CAR_2.csv',index=True)
        info_df.to_csv(f'{filePath}/csv/{filename}/{filename}_CAR_3.csv',index=False)
        rec_df.to_csv(f'{filePath}/csv/{filename}/{filename}_CAR_4.csv',index=False)
    else:
        try:
            os.mkdir(f'{filePath}/excel')
        except FileExistsError:
            pass
        with pd.ExcelWriter(f'{filePath}/excel/{filename}_CAR.xlsx') as writer:
            data_df.to_excel(writer,sheet_name='All data',index=False)
            pivot_df.to_excel(writer,sheet_name='Pivot data',index=True)
            info_df.to_excel(writer,sheet_name='Info',index=False)
            rec_df.to_excel(writer,sheet_name='Recommendation',index=False)

def create_loan(text):
    completeDF = {"Products":[],"Loan Institution":[],"date_opened":[],"Sanction/Credit Limit":[],"Balance":[],"EMI":[],"Paid Principle":[],"open":[],"Delinquencies":[]}
    countAcc = text.count("Acct # :")
    for i in range(countAcc):
        delinquecy = False
        accountNoIndex = text.find("Acct # :")
        text = text[accountNoIndex+1:]
        openIndex = get_index(text.find('Open: '),'Open: ')
        openValue = text[openIndex:(text.find("Date Reported: "))].strip()

        dateOpenedIndex = get_index(text.find('Date Opened: '),'Date Opened: ')
        dateOpenedValue = text[dateOpenedIndex:(text.find("Type: "))].strip()
        try:
            date_object = datetime.datetime.strptime(dateOpenedValue, '%d-%m-%Y').date()
        except ValueError:
            date_object = 0
        # print(text)
        BalanceIndex = get_index(text.find('Balance: '),'Balance: ')
        Balance = text[BalanceIndex:(text.find('Open:'))]
        try:
            if(Balance[0] == "R"):
                Balance = Balance[4:]
            elif(Balance == ""):
                Balance = 0
            try:
                Balance = int(Balance.replace(',',''))
            except ValueError:
                Balance = 0
        except IndexError:
            Balance = 0
        # Find Loan Institution
        instiutionIndex = get_index(text.find('Institution : '),'Institution : ')
        instiutionName = text[instiutionIndex:(text.find('Past Due Amount'))-1]

        # Find Products of loan
        ProductsIndex = get_index(text.find('Type: '),'Type: ')
        ProductsName = text[ProductsIndex:(text.find('Last Payment:'))-1]

        if(ProductsName not in ["Personal Loan","Business Loan","Credit Card","Home Loan","Auto Loan"]):
            ProductsName = "4_Others"
        elif(ProductsName == "Credit Card"):
            ProductsName = "1_CreditCard"
        elif(ProductsName == "Personal Loan"):
            ProductsName = "3_PersonalLoan"
        elif(ProductsName == "Business Loan"):
            ProductsName = "2_BusinessLoan"
        # Find EMI
        EMIIndex = get_index(text.find('Monthly Payment Amount: '),'Monthly Payment Amount:')
        EMIValue = text[EMIIndex:(text.find('Credit Limit:'))-1]
        if(EMIValue == ''):
            EMIValue = 0
        else:
            EMIValue = EMIValue[4:]
            try:
                EMIValue = int(EMIValue.replace(',',''))
            except ValueError:
                EMIValue = 0
        
        if(ProductsName == '1_CreditCard'):
            creditIndex = get_index(text.find('Credit Limit:'),"Credit Limit: Rs. ")
            creditLimit = text[creditIndex:text.find('Collateral Value')-1]
            try:
                sanction_credit = int(creditLimit.replace(',',''))
            except ValueError:
                sanction_credit = 0
            EMIValue = Balance*0.05
        else:
            sanctionIndex = get_index(text.find('Sanction Amount :'),"Sanction Amount : ")
            sanctionLimit = text[sanctionIndex:text.find('Reason:')]
            # print(sanctionLimit)
            if(sanctionLimit == ''):
                sanction_credit = 0
            else:
                sanctionLimit = sanctionLimit[4:]
                try:
                    sanction_credit = int(sanctionLimit.replace(',',''))
                except ValueError:
                    sanction_credit = 0
        AccountIndex = get_index(text.find('Account Status: '),'Account Status: ')
        AccountStatus = text[AccountIndex:text.find('Asset Classification')].strip()
        if(AccountStatus in [" ","Closed Account","Standard","Current Account"]):
            delinquecy = False
        else:
            delinquecy = True
        completeDF['Balance'].append(int(Balance))
        completeDF['Loan Institution'].append(instiutionName.strip())
        completeDF['Products'].append(ProductsName.strip())
        completeDF['Sanction/Credit Limit'].append(int(sanction_credit))
        completeDF['EMI'].append(int(EMIValue))
        completeDF['Paid Principle'].append(int(sanction_credit-Balance))
        completeDF['open'].append(openValue)
        completeDF['Delinquencies'].append(delinquecy)
        completeDF['date_opened'].append(date_object)
    return completeDF

folder_loc = input("Enter folder location:")
# Create a list of all files in the folder
files = os.listdir(folder_loc)
# Create a list of all files with .pdf extension
pdf_files = [f for f in files if f.endswith('.pdf')]
for file in pdf_files:
    print("For name",file)
    salary = int(input("enter salary:"))
    pdfFileObj = open(folder_loc+"/"+file, 'rb')
    complete_String = ""
    pdfReader = PyPDF2.PdfFileReader(pdfFileObj)
    for i in range(pdfReader.numPages):
        pageObj = pdfReader.getPage(i).extract_text()
        complete_String += pageObj
    riskIndex = get_index(complete_String.find("Equifax Risk Score 3.1 "), "Equifax Risk Score 3.1 ")
    riskValue = int(complete_String[riskIndex:(complete_String.find("1. "))].strip())
    nameIndex = get_index(complete_String.find("Consumer Name: "),"Consumer Name: ")
    nameValue = complete_String[nameIndex:(complete_String.find("Personal Information"))].strip().capitalize()
    finalDF = create_loan(complete_String)
    data_df = pd.DataFrame.from_dict(finalDF)
    data_df['open'] = data_df['open'].map({
        'Yes': True,
        'No': False
    })
    data_df = data_df.loc[data_df['open']==True]
    data_df.sort_values(by=['Products'],ascending=True,inplace=True)
    # drop row where balance is 0 and Delinquencies is true and emi is 0
    data_df = data_df.loc[(data_df['Balance']!=0) | (data_df['Delinquencies']==True) | (data_df['EMI']!=0)]
    # emi == 0
    data_df['Paid Principle'] = data_df['Paid Principle'].apply(lambda x: 0 if x<0 else x)
    if(salary <= 50000):
        FOIR = salary*0.5
    elif(salary > 50000 and salary <= 150000):
        FOIR = salary*0.6
    else:
        FOIR = salary*0.7
    delinquency = data_df['Delinquencies'].sum()
    if(delinquency>0):
        delinquency = True
    else:
        delinquency = False
    disposable = FOIR - data_df['EMI'].sum()
    data_df.drop(['open'],axis=1,inplace=True)
    # create a total dictionary
    total_dict = {
        'Products': 'Total',
        'Balance': data_df['Balance'].sum(),
        'EMI': data_df['EMI'].sum(),
        'Paid Principle': data_df['Paid Principle'].sum(),
        'Sanction/Credit Limit': data_df['Sanction/Credit Limit'].sum(),
        'Foir': FOIR,
        'Disposable': disposable,
        "salary": salary
    }
    total_dict = pd.DataFrame(total_dict,index=[0])
    data_df = pd.concat([data_df,total_dict],ignore_index=False)
    pivot_df = pd.pivot_table(data_df,index = ["Products"], values=['Sanction/Credit Limit','Balance','EMI','Paid Principle'], aggfunc=np.sum, fill_value=0)
    pivot_df['FOIR'] = FOIR
    pivot_df['Disposable'] = disposable
    info_df = {
        "Name":[nameValue],
        "Credit Score":[riskValue],
        "Salary":[salary],
    }
    # RECOMMENDATIONS
    new_df = data_df.copy()
    new_df['date_diff'] = new_df.apply(lambda x: diff_month(datetime.date.today(), x['date_opened']), axis=1)
    new_df = new_df.drop(new_df[(new_df['date_diff'] < 12) & (new_df['Products'].isin(['3_PersonalLoan','5_AutoLoan','6_HouseLoan']))].index)

    recommendation = ""
    recommendation_df = {"Recommendation":[],"New PL":[],"Top Up":[],"Reduce":[],"Remove":[]}
    no_of_delinquecy = data_df['Delinquencies'].sum()
    if(disposable>0):
        new_pl = int(get_new_PL(disposable))
        recommendation_df["New PL"].append(new_pl)
        recommendation+=f"You are eligible for a new Personal Loan of ₹{new_pl}"
    else:
        recommendation+="You are not eligible for a new Personal Loan"

    top_up_label = get_top_up(new_df)
    if(len(top_up_label)>0 and top_up_label[1]>0):
        recommendation_df["Top Up"].append(top_up_label)
        recommendation+=f" and a Top Up of ₹{top_up_label[1]} on your {top_up_label[0]}"
    else:
        recommendation+=". There is no Top Up available"
    filename = os.path.basename(file).split('.')[0]
    recommendation_df = pd.DataFrame(recommendation_df)
    info_df = pd.DataFrame(info_df)
    save_as_csv(pivot_df= pivot_df,filename=filename,data_df=data_df,csv=False,info_df=pd.DataFrame(info_df),rec_df=pd.DataFrame(recommendation_df),filePath=folder_loc)

# regex for month-date
# month_date = re.compile(r'(\d{1,2})-(\d{1,2})')
