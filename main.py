# importing required modules
import PyPDF2
import numpy as np
import datetime
import pandas as pd
import re
import os

def get_index(firstIndex,string):
    return int(firstIndex)+int(len(string))

def check_delinquencies(text):
    pass


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

def getCases(top_up:int,case_df:dict,pivot:pd.DataFrame):
    global recommendation_string
    tentative_string = ""
    balance = pivot['Balance'].to_list()
    if (len(balance)>0):
        for i in range(len(balance)):
            productBalance = balance[i]
            if(top_up == 0):
                break
            elif(productBalance>top_up):
                # REDUCE CONDITION WILL HAVE {REDUCE PRODUCT: OUTSTANDING PRODUCT VALUE}
                case_df['Sentence'].append(f"Reduce {pivot.index[i]}")
                tentative_string+=f", Reduce {pivot.index[i]}"
                outstandingProductBalance = productBalance - top_up
                top_up = 0
                case_df["Value"].append(outstandingProductBalance)
            elif(productBalance<top_up):
                # REMOVE CONDITION WILL HAVE {REMOVE PRODUCT: TOP UP VALUE}
                case_df['Sentence'].append(f"Remove {pivot.index[i]}")
                tentative_string+=f", Remove {pivot.index[i]}"
                top_up = top_up - productBalance
                productBalance = 0
                case_df['Value'].append(top_up)
            else:
                print("No recommendation")
        recommendation_string+=" We recommend you use this to "+tentative_string
    else:
        recommendation_string+=""
    return case_df


def get_top_up(new_df:pd.DataFrame,new_pl:int):
    global recommendation_string
    new_df['date_diff'] = new_df.apply(lambda x: diff_month(datetime.date.today(), x['date_opened']), axis=1)
    # emi must be greater than 12 months
    new_df = new_df.drop(new_df[(new_df['date_diff'] < 12) & (new_df['Products'].isin(['3_PersonalLoan','5_AutoLoan','6_HousingLoan']))].index)
    new_df.sort_values(by=['Paid Principle'],ascending=False,inplace = True)
    top_up_df = new_df.loc[new_df['Products'].isin(['3_PersonalLoan','5_AutoLoan','6_HousingLoan'])]
    new_df.drop(top_up_df.index,inplace=True)
    top_up_df = top_up_df.drop_duplicates(subset=['Loan Institution'],keep='first')
    new_df = pd.concat([new_df,top_up_df])
    pivot = pd.pivot_table(top_up_df,values=['Paid Principle',"Balance"],index=['Products'],aggfunc=np.sum,fill_value=0)
    top_up_list = []
    try:
        top_up_list.append(np.where(pivot.index == '3_PersonalLoan')[0][0])
    except IndexError:
        pass
    try:
        top_up_list.append(np.where(pivot.index == '5_AutoLoan')[0][0])
    except IndexError:
        pass
    try:
        top_up_list.append(np.where(pivot.index == '6_HousingLoan')[0][0])
    except IndexError:
        pass
    pivot = pivot.reset_index()
    pivot['Products'] = pivot['Products'].map({
        '1_CreditCard':'Credit Card',
        '2_BusinessLoan':'Business Loan',
        '3_PersonalLoan':'Personal Loan',
        '4_Others':'Others',
        '5_AutoLoan':'Auto Loan',
        '6_HousingLoan':'House Loan',
    })
    pivot = pivot.dropna(subset=['Products'],axis=0)
    pivot = pivot.set_index('Products')
    case_df = {"Sentence":[],"Value":[]}
    products = list(set([pivot.index[x] for x in top_up_list]))
    # print(top_up_list)
    if(len(top_up_list) > 0):
        if(len(products)):
            recommendation_string+="You can get a top up on "+', '.join(products)+" based on the amount you have already paid for. "
        else:
            recommendation_string+="No top up available."
        for i in range(len(top_up_list)):
            # case_df.append({"Sentence":[f"Top up {pivot.index[top_up_index]}"],"Value":[pivot.loc[pivot.index[top_up_index]]['Paid Principle']]})
            top_up_index = top_up_list[i]
            case_df['Sentence'].append(f"Top up {pivot.index[top_up_index]}")
            case_df['Value'].append(pivot.loc[pivot.index[top_up_index]]['Paid Principle'])
            top_up = pivot.loc[pivot.index[top_up_index]]['Paid Principle']
            if(i==0):
                local_pivot = pivot.loc[pivot.index[0:top_up_list[i]]]
            else:
                local_pivot = pivot.loc[pivot.index[top_up_list[i-1]:top_up_list[i]]]
            case_df = getCases(top_up=top_up,case_df =case_df,pivot =local_pivot)
    else:
        recommendation_string+=""
    if(new_pl>0):
        case_df['Sentence'].append("New Personal Loan")
        case_df['Value'].append(new_pl)
    else:
        pass
    # print(case_df,products,top_up_list,recommendation_string)
    return pd.DataFrame(case_df)


def diff_month(d1, d2):
    try:
        return (d1.year - d2.year) * 12 + d1.month - d2.month
    except AttributeError:
        return 0

def save_as_csv(data_df:pd.DataFrame,pivot_df:pd.DataFrame,csv,filename,info_df:pd.DataFrame,rec_df:pd.DataFrame,case_df:pd.DataFrame,filePath):
    # remove date_opened,foir,disposable,salary
    data_df = data_df.drop(columns=['date_opened','Foir','Disposable','salary'])
    if(csv):
        try:
            print("Hello")
            os.mkdir(f'{filePath}/csv')
        except FileExistsError:
            pass
        data_df.to_csv(f'{filePath}/csv/{filename}_CAR_1.csv',index=False)
        pivot_df.to_csv(f'{filePath}/csv/{filename}_CAR_2.csv',index=True)
        info_df.to_csv(f'{filePath}/csv/{filename}_CAR_3.csv',index=False)
        rec_df.to_csv(f'{filePath}/csv/{filename}_CAR_4.csv',index=False)
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
            print(case_df.shape)
            if len(case_df) > 3:
                print("Hello")
                case_1 = case_df.iloc[:3]
                case_2 = case_df.iloc[3:]
                case_1.to_excel(writer,sheet_name='Case 1',index=False)
                case_2.to_excel(writer,sheet_name='Case 2',index=False)
            else:
                print("Hello 2")
                case_df.to_excel(writer,sheet_name='Case 1',index=False)

def create_loan(text):
    completeDF = {"Products":[],"Loan Institution":[],"date_opened":[],"Sanction/Credit Limit":[],"Balance":[],"EMI":[],"Paid Principle":[],"open":[],"Delinquencies":[]}
    countAcc = text.count("Acct # :")
    for i in range(countAcc):
        delinquecy = False
        accountNoIndex = text.find("Acct # :")
        text = text[accountNoIndex+1:]
        # print(accountNoIndex)
        # delinquencies
        # delinquecy_count =check_delinquencies(text)
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

        if(ProductsName not in ["Personal Loan","Business Loan","Credit Card","Housing Loan","Auto Loan"]):
            ProductsName = "4_Others"
        elif(ProductsName == "Credit Card"):
            ProductsName = "1_CreditCard"
        elif(ProductsName == "Business Loan"):
            ProductsName = "2_BusinessLoan"
        elif(ProductsName == "Personal Loan"):
            ProductsName = "3_PersonalLoan"
        elif(ProductsName == "Auto Loan"):
            ProductsName = "5_AutoLoan"
        elif(ProductsName == "Housing Loan"):
            ProductsName = "6_HousingLoan"
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
        completeDF['Delinquencies'].append(0)
        completeDF['date_opened'].append(date_object)
    return completeDF

# folder_loc = input("Enter folder location:")
folder_loc = "/Users/nilaygaitonde/Downloads"
# Create a list of all files in the folder
files = os.listdir(folder_loc)
# Create a list of all files with .pdf extension
pdf_files = [f for f in files if f.endswith('.pdf')]
for file in pdf_files:
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
    # salary = int(input(f"Enter salary for {nameValue}:"))
    salary = 150000
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
    pivot_df = pd.pivot_table(data_df,index = ["Products"], values=['Sanction/Credit Limit','Balance','EMI','Paid Principle','Delinquencies'], aggfunc=np.sum, fill_value=0)
    pivot_df['FOIR'] = FOIR
    pivot_df['Disposable'] = disposable
    info_df = {
        "Name":[nameValue],
        "Credit Score":[riskValue],
        "Salary":[salary],
    }
    pivot_df = pivot_df[['Sanction/Credit Limit','Balance','EMI','Paid Principle','FOIR','Disposable']]
    # RECOMMENDATIONS
    new_df = data_df.copy()
    recommendation_string = ""
    new_pl=0
    if(disposable>0):
        new_pl = int(get_new_PL(disposable))
        recommendation_string+=f"You are eligible for a new Personal Loan of ₹{new_pl}. "
    else:
        recommendation_string+="You are not eligible for a new Personal Loan. "
    info_df = pd.DataFrame(info_df)
    case_df = get_top_up(new_df=new_df,new_pl=new_pl)
    recommendation = {"Conclusion":[recommendation_string]}
    save_as_csv(pivot_df= pivot_df,filename=nameValue,data_df=data_df,csv=False,info_df=pd.DataFrame(info_df),rec_df=pd.DataFrame(recommendation),case_df = case_df,filePath=folder_loc)

# regex for month-date
# month_date = re.compile(r'(\d{1,2})-(\d{1,2})')
