# importing required modules
import PyPDF2
import re
from datetime import datetime
import pandas as pd
import os

def get_index(firstIndex,string):
    return int(firstIndex)+int(len(string))

def save_as_csv(data_df,pivot_df,csv,filename):
    if(csv):
        data_df.to_csv(f'{filename}_1.csv',index=False)
        pivot_df.to_csv(f'{filename}_2.csv',index=True)
    else:
        with pd.ExcelWriter(f'{filename}.xlsx') as writer:
            data_df.to_excel(writer,sheet_name='Sheet1',index=False)
            pivot_df.to_excel(writer,sheet_name='Sheet2',index=True)

def create_loan(text,completeDF):
    completeDF = {"type":[],"institution":[],"date_opened":[],"sanction_credit":[],"balance":[],"emi":[],"paid_principle":[],"open":[],"delinquecy":[]}
    countAcc = text.count("Acct # :")
    for _ in range(countAcc):
        delinquecy = False
        accountNoIndex = text.find("Acct # :")
        text = text[accountNoIndex+1:]
        openIndex = get_index(text.find('Open: '),'Open: ')
        openValue = text[openIndex:(text.find("Date Reported: "))].strip()

        dateOpenedIndex = get_index(text.find('Date Opened: '),'Date Opened: ')
        dateOpenedValue = text[dateOpenedIndex:(text.find("Type: "))].strip()
        try:
            date_object = datetime.strptime(dateOpenedValue, '%d-%m-%Y').date()
        except ValueError:
            pass
        # print(text)
        balanceIndex = get_index(text.find('Balance: '),'Balance: ')
        balance = text[balanceIndex:(text.find('Open:'))]
        if(balance[0] == "R"):
            balance = balance[4:]
        balance = int(balance.replace(',',''))
        # Find institution
        instiutionIndex = get_index(text.find('Institution : '),'Institution : ')
        instiutionName = text[instiutionIndex:(text.find('Past Due Amount'))-1]

        # Find type of loan
        typeIndex = get_index(text.find('Type: '),'Type: ')
        typeName = text[typeIndex:(text.find('Last Payment:'))-1]

        # TODO:::::::: FILL NAMES OF LOAN TYPES

        if(typeName not in ["Personal Loan","Business Loan","Credit Card","","Auto Loan"]):
            typeName = "4_Others"
        elif(typeName == "Credit Card"):
            typeName = "1_CreditCard"
        elif(typeName == "Personal Loan"):
            typeName = "3_PersonalLoan"
        elif(typeName == "Business Loan"):
            typeName = "2_BusinessLoan"
        # Find EMI
        emiIndex = get_index(text.find('Monthly Payment Amount: '),'Monthly Payment Amount:')
        emiValue = text[emiIndex:(text.find('Credit Limit:'))-1]
        if(emiValue == ''):
            emiValue = 0
        else:
            emiValue = emiValue[4:]
            try:
                emiValue = int(emiValue.replace(',',''))
            except ValueError:
                emiValue = 0
        
        if(typeName == '1_CreditCard'):
            creditIndex = get_index(text.find('Credit Limit:'),"Credit Limit: Rs. ")
            creditLimit = text[creditIndex:text.find('Collateral Value')-1]
            try:
                sanction_credit = int(creditLimit.replace(',',''))
            except ValueError:
                sanction_credit = 0
            emiValue = balance*0.05
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
        completeDF['balance'].append(int(balance))
        completeDF['institution'].append(instiutionName.strip())
        completeDF['type'].append(typeName.strip())
        completeDF['sanction_credit'].append(int(sanction_credit))
        completeDF['emi'].append(int(emiValue))
        completeDF['paid_principle'].append(int(sanction_credit-balance))
        completeDF['open'].append(openValue)
        completeDF['delinquecy'].append(delinquecy)
        completeDF['date_opened'].append(date_object)
    return completeDF

folder_loc = input("Enter folder location:")
# Create a list of all files in the folder
files = os.listdir(folder_loc)
# Create a list of all files with .pdf extension
pdf_files = [f for f in files if f.endswith('.pdf')]
finalDF = {"type":[],"institution":[],"sanction_credit":[],"balance":[],"emi":[],"paid_principle":[],"open":[],"delinquecy":[],"date_opened":[]}
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
    print(riskValue)
    newDF = create_loan(complete_String,finalDF)
    [finalDF["type"].append(i) for i in newDF["type"]]
    [finalDF["institution"].append(i) for i in newDF["institution"]]
    [finalDF["sanction_credit"].append(i) for i in newDF["sanction_credit"]]
    [finalDF["balance"].append(i) for i in newDF["balance"]]
    [finalDF["emi"].append(i) for i in newDF["emi"]]
    [finalDF["paid_principle"].append(i) for i in newDF["paid_principle"]]
    [finalDF['open'].append(i) for i in newDF["open"]]
    [finalDF['delinquecy'].append(i) for i in newDF["delinquecy"]]
    [finalDF['date_opened'].append(i) for i in newDF["date_opened"]]
    data_df = pd.DataFrame.from_dict(finalDF)
    data_df['open'] = data_df['open'].map({
        'Yes': True,
        'No': False
    })
    data_df = data_df.loc[data_df['open']==True]
    data_df.sort_values(by=['type'],ascending=True,inplace=True)
    data_df = data_df.loc[(data_df['balance']!=0) | (data_df['delinquecy']==True)]
    data_df['paid_principle'] = data_df['paid_principle'].apply(lambda x: 0 if x<0 else x)
    data_df.groupby('type').sum()
    df1=pd.DataFrame()
    if(salary <= 50000):
        FOIR = salary*0.5
    elif(salary > 50000 and salary <= 150000):
        FOIR = salary*0.6
    else:
        FOIR = salary*0.7
    delinquency = data_df['delinquecy'].sum()
    if(delinquency>0):
        delinquency = True
    else:
        delinquency = False
    disposable = FOIR - data_df['emi'].sum()
    # -------------------OUTPUT-------------------
    print("FOIR: ",FOIR)
    print("emi",data_df['emi'].sum())
    print("Disposable: ",disposable)
    print("Delinuency:",delinquency)
    if(delinquency):
        print("You have delinuency in your loan and you are not eligible for loan")
    else:
        if(disposable>0):
            print("You are eligible for loan")
        else:
            print("You are not eligible for loan")
    # data_df.drop(['open'],axis=1,inplace=True)
    sum_df = {
        'type': 'Total',
        'sanction_credit': data_df['sanction_credit'].sum(),
        'balance': data_df['balance'].sum(),
        'emi': data_df['emi'].sum(),
        'paid_principle': data_df['paid_principle'].sum(),
        'delinquecy': data_df['delinquecy'].sum(),
        'foir': FOIR,
        'disposable': FOIR - data_df['emi'].sum(),
    }
    sum_df = pd.DataFrame(sum_df,index=[0])
    pivot_df = data_df.groupby('type').sum()
    pivot_df = pivot_df.reset_index()
    pivot_df = pivot_df.append(sum_df,ignore_index=True)
    pivot_df.set_index('type',inplace=True)
    filename = os.path.basename(file).split('.')[0]
    save_as_csv(pivot_df= pivot_df,filename=filename,data_df=data_df,csv=False)