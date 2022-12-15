# importing required modules
import PyPDF2
import numpy as np
import datetime
import pandas as pd
import re
import os

def rename_products(df:pd.DataFrame):
    df = df.reset_index()
    df['Products'] = df['Products'].map({
        '1_CreditCard':'Credit Card',
        '2_BusinessLoan':'Business Loan',
        '3_PersonalLoan':'Personal Loan',
        '4_Others':'Others',
        '5_AutoLoan':'Auto Loan',
        '6_HousingLoan':'House Loan',
    })
    df = df.set_index('Products')
    return df

def get_index(firstIndex:int,string:str):
    return int(firstIndex)+int(len(string))

def recommend_delinquency(pivot_df:pd.DataFrame):
    global recommendation_string
    # get pivot index for delinquency>0
    delinquency_index = np.where(pivot_df['Delinquencies']>0)[0]
    pivot_df = rename_products(pivot_df)
    products = list(set([pivot_df.index[x] for x in delinquency_index]))
    products = [x for x in products if x == x]
    recommendation_string="Your Credit report shows that you have delinquencies in "+', '.join(products)+","+" due to which you are not eligible for a Loan. We suggest you to Clear your Delinquencies in"+', '.join(products)+","+" so your chances of Loan approval gets Improved as well as it will also help you to maintain Good Credit Score."

def get_new_PL(disposable:int):
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

def getCases(top_up:int,case_df:dict,pivot:pd.DataFrame,new_pl:int):
    global recommendation_string
    tentative_string = []
    balance = pivot['Balance'].to_list()
    for i in range(len(balance)):
        productBalance = balance[i]
        if(top_up == 0):
            break
        elif(productBalance>top_up):
            # REDUCE CONDITION WILL HAVE {REDUCE PRODUCT: OUTSTANDING PRODUCT VALUE}
            case_df['Sentence'].append(f"Outstanding {pivot.index[i]} balance")
            case_df['Value'].append(productBalance)
            case_df['Sentence'].append(f"Remaining {pivot.index[i]} balance")
            tentative_string.append(f", Reduce {pivot.index[i]}")
            balance[i] = productBalance - top_up
            case_df["Value"].append(productBalance-top_up)
            top_up = 0
        elif(productBalance<top_up):
            # REMOVE CONDITION WILL HAVE {REMOVE PRODUCT: TOP UP VALUE}
            case_df['Sentence'].append(f"Outstanding {pivot.index[i]} balance")
            case_df['Sentence'].append(f"Remaining Top Up balance")
            case_df['Value'].append(productBalance)
            tentative_string.append(f", Remove {pivot.index[i]}")
            top_up = top_up - productBalance
            balance[i] = 0
            case_df['Value'].append(top_up)
        else:
            print("No recommendation")
    tentative_string = set(tentative_string)
    recommendation_string+=" We recommend you use this to "+" ".join(tentative_string)+"."
    return case_df,balance

def get_newpl_cases(case_df, pivot, new_pl, balance):
    global recommendation_string
    tentative_string =[]
    if(balance == 0):
        balance = pivot['Balance'].to_list()
    else:
        pass
    balance = [i for i in balance if i != 0]
    print(balance)
    if(len(balance) > 0):
        for i in range(len(balance)):
            productBalance = balance[i]
            if(productBalance == 0):
                break
            elif(new_pl == 0):
                    break
            elif(productBalance>new_pl):
                # REDUCE CONDITION WILL HAVE {REDUCE PRODUCT: OUTSTANDING PRODUCT VALUE}
                case_df['Sentence'].append(f'Outstanding {pivot.index[i]} balance')
                case_df['Value'].append(productBalance)
                case_df['Sentence'].append(f"Remaining {pivot.index[i]} balance")
                tentative_string.append(f", Reduce {pivot.index[i]}")
                balance[i] = productBalance - new_pl
                new_pl = 0
                case_df["Value"].append(productBalance-new_pl)
            elif(productBalance<new_pl):
                # REMOVE CONDITION WILL HAVE {REMOVE PRODUCT: TOP UP VALUE}
                case_df['Sentence'].append(f"Outstanding {pivot.index[i]} balance")
                case_df['Value'].append(productBalance)
                case_df['Sentence'].append(f"Remaining New PL balance")
                tentative_string.append(f", Remove {pivot.index[i]}")
                new_pl = new_pl - productBalance
                balance[i] = 0
                case_df['Value'].append(new_pl)
            else:
                print("No recommendation")
        tentative_string = set(tentative_string)
        recommendation_string+=" We recommend you use this to "+" ".join(tentative_string)+"."
    else:
        pass
    return case_df


def get_top_up(new_df:pd.DataFrame,new_pl:int):
    global recommendation_string
    new_pl_list = []
    new_df['date_diff'] = new_df.apply(lambda x: diff_month(datetime.date.today(), x['date_opened']), axis=1)
    # emi must be greater than 12 months
    new_df = new_df.drop(new_df[(new_df['date_diff'] < 12) & (new_df['Products'].isin(['3_PersonalLoan','5_AutoLoan','6_HousingLoan']))].index)
    new_df.sort_values(by=['Paid Principle'],ascending=False,inplace = True)
    top_up_df = new_df.loc[new_df['Products'].isin(['3_PersonalLoan','5_AutoLoan','6_HousingLoan'])]
    new_df.drop(top_up_df.index,inplace=True)
    top_up_df = top_up_df.drop_duplicates(subset=['Loan Institution'],keep='first')
    new_df = pd.concat([new_df,top_up_df])
    pivot = pd.pivot_table(new_df,values=['Paid Principle',"Balance"],index=['Products'],aggfunc=np.sum,fill_value=0)
    # pivot.set_index('Products',inplace=True)
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
    try:
        new_pl_list.append(np.where(pivot.index == '1_CreditCard')[0][0])
    except IndexError:
        pass
    try:
        new_pl_list.append(np.where(pivot.index == '2_BusinessLoan')[0][0])
    except IndexError:
        pass
    pivot = pivot.reset_index()
    pivot = rename_products(pivot)
    # pivot = pivot.dropna(subset=['Products'],axis=0)
    case_df = {"Sentence":[],"Value":[]}
    products = list(set([pivot.index[x] for x in top_up_list]))
    products = [x for x in products if x == x]
    top_up_list.reverse()
    if(len(top_up_list) > 0):
        print("Hello world")
        if(len(products)>0):
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
            val = getCases(top_up=top_up,case_df =case_df,pivot =local_pivot,new_pl=new_pl)
            case_df = val[0]
            balance = val[1]
    else:
        recommendation_string+=""
    if(new_pl>0):
        case_df['Sentence'].append("New Personal Loan")
        case_df['Value'].append(new_pl)
        recommendation_string+=f"You are eligible for a new Personal Loan of ₹{new_pl}. "
        # generate local pivot with all pivot.index in new_pl_list
        local_pivot = pivot.loc[pivot.index[new_pl_list]]
        try:
            case_df = get_newpl_cases(case_df=case_df,pivot=local_pivot,new_pl=new_pl,balance=balance)
        except UnboundLocalError:
            case_df = get_newpl_cases(case_df=case_df,pivot=local_pivot,new_pl=new_pl,balance=0)
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
    # data_df = data_df.drop(columns=['date_opened','Foir','Disposable','salary'])
    pivot_df = rename_products(pivot_df)
    if(csv):
        try:
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
            if len(case_df) > 3:
                case_1 = case_df.iloc[:3]
                case_2 = case_df.iloc[3:]
                case_1.to_excel(writer,sheet_name='Case 1',index=False)
                case_2.to_excel(writer,sheet_name='Case 2',index=False)
            else:
                case_df.to_excel(writer,sheet_name='Case 1',index=False)

def create_loan(text:str):
    completeDF = {"Products":[],"Loan Institution":[],"date_opened":[],"Sanction/Credit Limit":[],"Balance":[],"EMI":[],"Paid Principle":[],"open":[],"Delinquencies":[]}
    countAcc = text.count("Acct # :")
    for i in range(countAcc):
        delinquecy = False
        accountNoIndex = text.find("Acct # :")
        text = text[accountNoIndex+1:]

        # DELINQUENCIES

        delinquenciesIndex = get_index(text.find("Suit Filed Status:"),"Suit Filed Status:")
        if(text[delinquenciesIndex+1].strip() == "H"):
            delinquencyString = text[(delinquenciesIndex+len("HistoryAccount Status:Asset Classification:Suit Filed Status:")+4):(text.find("Acct # :"))]
            # print(delinquencyString)
            # Get all index of string "-22" is present in the delinquency string
            index = [m.start() for m in re.finditer('-22', delinquencyString)]
            if(len(index)>0):
                try:
                    six_months = index[0:7]
                except IndexError:
                    six_months = index
                delinquencyString = delinquencyString[six_months[0]:(six_months[-1]+2)]
                delinquenciesCount = (delinquencyString.count("+")+delinquencyString.count("CLSD")+delinquencyString.count("WOF")+delinquencyString.count("RCV"))
            else:
                delinquenciesCount = 0
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
        completeDF['Delinquencies'].append(delinquenciesCount)
        completeDF['date_opened'].append(date_object)
    return completeDF

folder_loc = input("Enter folder location:")
# folder_loc = "/Users/nilaygaitonde/Downloads"
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
    salary = int(input(f"Enter salary for {nameValue}:"))
    # salary = 50000
    finalDF = create_loan(complete_String)
    data_df = pd.DataFrame.from_dict(finalDF)
    data_df['open'] = data_df['open'].map({
        'Yes': True,
        'No': False
    })
    data_df = data_df.loc[data_df['open']==True]
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
    disposable = FOIR - data_df['EMI'].sum()
    data_df.drop(['open'],axis=1,inplace=True)
    show_df = data_df.copy()
    data_df['Products'] = data_df['Products'].map({
        'Credit Card': '1_CreditCard',
        'Business Loan':'2_BusinessLoan',
        'Personal Loan':'3_PersonalLoan',
        'Auto Loan':'5_AutoLoan',
        'Housing Loan':'6_HousingLoan',
    })
    data_df['Products'] = data_df['Products'].fillna('4_Others')
    data_df.sort_values(by=['Products'],ascending=True,inplace=True)
    # create a total dictionary
    total_dict = {
        'Products': 'Total',
        'Balance': data_df['Balance'].sum(),
        'EMI': data_df['EMI'].sum(),
        'Paid Principle': data_df['Paid Principle'].sum(),
        'Sanction/Credit Limit': data_df['Sanction/Credit Limit'].sum(),
        'Delinquencies': delinquency,
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
    pivot_df = pivot_df[['Sanction/Credit Limit','Balance','EMI','Paid Principle','Delinquencies','FOIR','Disposable']]
    # RECOMMENDATIONS
    new_df = data_df.copy()
    recommendation_string = ""
    new_pl=0
    if(disposable>0):
        new_pl = int(get_new_PL(disposable))
    else:
        recommendation_string+="You are not eligible for a new Personal Loan. "
    info_df = pd.DataFrame(info_df)
    if(delinquency > 0):
        recommend_delinquency(pivot_df)
        case_df = pd.DataFrame({"Conclusion":[recommendation_string]})
        rec_df = pd.DataFrame()
    else:
        case_df = get_top_up(new_df=new_df,new_pl=new_pl)
        case_df = pd.DataFrame(case_df)
        rec_df = pd.DataFrame({"Conclusion":[recommendation_string]})

    save_as_csv(pivot_df= pivot_df,filename=nameValue,data_df=show_df,csv=False,info_df=pd.DataFrame(info_df),rec_df=rec_df,case_df = case_df,filePath=folder_loc)