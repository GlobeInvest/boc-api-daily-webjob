import requests
import time
from datetime import datetime
from datetime import timedelta
import pandas
import json
import re
import sys

from dbservices_package.db_services import Db_request

from sendemail_package.Sendemail import SendEmails

from Logger_package.ALogger import Logger

EmailObj=SendEmails()


######################################################################################################################################################
############################################################### BANK API CLASS #######################################################################
######################################################################################################################################################
######################################################################################################################################################

class Bank_API():
    def __init__(self):
         #self.clinet_id='a14c73b4-794a-40f8-b5c7-e75d75fc9368'     
         self.clinet_id='bocapiclientid'
         #self.client_secret='iQ2jC7eW8dQ5uH6iC7aC5wW3cO5cW2xY3wQ7bF8dE5wX8kT6vC'
         self.client_secret='bocapiclientsecret'
         self.baseurl='https://apis.bankofcyprus.com/df-boc-org-prd/prod/psd2/'
         self.ouath_url='https://apis.bankofcyprus.com/df-boc-org-prd/prod/psd2/'
         self.redirect_uri='https://ftmsapp.azurewebsites.net'
         #self.TPPID='eb3cbe3f-87d1-4545-ae57-898a68b99550'  
         self.TPPID='bocapitppid'
         self.Activation_Subscriber_id=''
         self.Activation_Business_id=''
         self.Password=''
         self.OuathCode=''
         self.Activation_Oathcode=''
         self.Bank_name='BOC'
         self.__GetpasswordfromVault()
         self.origin_user_id=''
         self.de_origin_user_id=''
         self.subscription_id=''
         self.de_subscription_id=''
         self.selected_accounts=[]
         self.expiration_date=''
    
    def __GetpasswordfromVault(self):
        ValutLogger=Logger([self.clinet_id,self.client_secret,self.TPPID])
        self.clinet_id=ValutLogger.ListOfReturnValues[self.clinet_id].value
        self.client_secret=ValutLogger.ListOfReturnValues[self.client_secret].value
        self.TPPID=ValutLogger.ListOfReturnValues[self.TPPID].value

    def get_API_Token(self):
        GrantType='client_credentials'
        Scope='TPPOAuth2Security'
        url= self.baseurl+'oauth2/token'
        payload = "client_id="+self.clinet_id+"&client_secret="+self.client_secret+"&grant_type=client_credentials&scope=TPPOAuth2Security"

        headers = {'Content-Type': "application/x-www-form-urlencoded",
                'cache-control': "no-cache",
                'Host': "apis.bankofcyprus.com"}
 
        res = requests.request("POST", url, data=payload, headers=headers)
        print('API token response code: {}, {}'.format(res.status_code, res))
        
        if (res.status_code==200) :   
            respond=json.loads(res.text)
            OuathCode=respond['access_token']
            self.OuathCode=OuathCode
            return 1
        else : 
            return 0 
        
        
    def get_subscription_details(self, sub_id, origin_id):
        url = f"https://apis.bankofcyprus.com/df-boc-org-prd/prod/psd2/v1/subscriptions/{sub_id}"

        payload = {}
        headers = {
            'Authorization': f'Bearer {self.OuathCode}',
            'Content-Type': 'application/json',
            'originUserId': f'{origin_id}',
            'timestamp': '1695368038',
            'journeyId': '46621fdf-d673-4173-94b8-70b98a7c67e7',
            'Cookie': '7db62af7e227442d7d8cc8e7773475f7=9c1ce5ce174ef0e9f76b2c67b708705b; TS010d5713=0179594e119de6187fbd2c1025469fd3108670b955bb4573e9d0f1850132875a7e5de522bb98725dc0c0bc1af4f7295b101eeca562f7e5350cafa717dbc8383661c00cd90a'
        }

        response = requests.request("GET", url, headers=headers, data=payload)

        if response.status_code == 200:
            data = response.json()[0]
            self.subscription_status = data['status']
            if self.subscription_status == 'ACTV':
                self.selected_accounts = [acc_id['accountId'] for acc_id in data['selectedAccounts']]
                self.expiration_date = data['expirationDate']
                print(f'[OK] - Subscription id {sub_id} is ACTIVE until {self.expiration_date} for {len(self.selected_accounts)} selected accounts')
                return True
        else:
            print(f'[WARN] - Subscription details - {response.status_code} - Failed retrieving subscription from API - {response.text}')
            return False
        
    def get_account_details(self, account):

        url = f"https://apis.bankofcyprus.com/df-boc-org-prd/prod/psd2/v1/accounts/{account.Account_id}"

        payload = {}
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + self.OuathCode,
            'subscriptionId': account.subscriptionId,
            'originUserId': account.originid,
            'journeyId': '10b66afa-7c9e-4181-8566-020b804f98eb',
            'timeStamp': '1691742512',
            # 'Cookie': '7db62af7e227442d7d8cc8e7773475f7=c08beb4d59bdc1356ad507f5a3713fdc; TS010d5713=0179594e116c2250218ecd6b2d49ece23262d2bbcbf1f8ff52d0291d83277efb8009a820c68c3a201acec5e1c504ea4c8a4a62b2a2b8348dfd52f3f8931a652c23d3238f17'
        }

        response = requests.request("GET", url, headers=headers, data=payload)

        if response.status_code == 200:
            return json.loads(response.text)[0]['currency']
        else:
            return None

    def get_balance_from_account_balances(self, balances_json, balance_type):
        for row in balances_json:
            if balance_type in str(row['balanceType']).lower():
                return row['amount']
        return 0
     
    def get_Transactions(self,Run_Dates,Account):
        
        print("get")
        if len(Run_Dates)==0:
            return []
        print(f"get transactions from {Run_Dates[0]} to {Run_Dates[1]}")
        
        From_Date=str(Run_Dates[0].day)+'/'+str(Run_Dates[0].month)+'/'+str(Run_Dates[0].year)
        To_date=str(Run_Dates[1].day)+'/'+str(Run_Dates[1].month)+'/'+str(Run_Dates[1].year)         
        url= self.baseurl+'v1/accounts/'+Account.Account_id+'/statement'
        querystring = {"client_id":self.clinet_id,
                "client_secret":self.client_secret,
                "startDate":From_Date,"endDate":To_date}
        payload = ""
        headers = {
            'Content-Type': "application/json",
            'Authorization': "Bearer "+self.OuathCode,
            'subscriptionId':Account.subscriptionId,
            'originUserId': Account.originid,
                'tppId': self.TPPID,
                'journeyId': "abc",
                'timeStamp': "1557748446",
                'cache-control': "no-cache",   
                }           
        res = requests.request("GET", url, data=payload, headers=headers, params=querystring)
        print("res.status_code "+str(res.status_code))

        if (res.status_code==200):
            Account.to_update=1
            response=json.loads(res.text)
            Account.Raw_Transactions=response['transaction']
            Account.Currency=str(response['account']['currency'])
            Account.Company=response['account']['accountName']

            balances_obj = response['account']['balances']
            Account.available_balance=self.get_balance_from_account_balances(balances_json=balances_obj, balance_type='available')#float((respond['account']['balances'])[0]['amount'] or 0)
            Account.current_balance=self.get_balance_from_account_balances(balances_json=balances_obj, balance_type='current')#float((respond['account']['balances'])[1]['amount'] or 0)
            Account.start_balance=self.get_balance_from_account_balances(balances_json=balances_obj, balance_type='start')#float((respond['account']['balances'])[2]['amount'] or 0)
            Account.end_balance=self.get_balance_from_account_balances(balances_json=balances_obj, balance_type='end')#float((respond['account']['balances'])[3]['amount'] or 0)
            
            Account.account_type=response['account']['accountType']
            Account.run_type='Transactions'

        elif (res.status_code>=400 and res.status_code<500): ##No transactions    
            response=json.loads(res.text)
            Account.to_update=1
            Account.check_expration_date()
            if Account.subscription_expire_date<=datetime.today().date():     
                EmailObj.SendEmail("[BOC - 400 - ERROR] - Account need to reactivate "+Account.IBAN,'')
                return 1
            elif 'error' in response:
                if type(response['error']) is dict and 'description' in response['error'] and 'No transactions found' in response['error']['description']:
                    print(f"[WARN] - {res.status_code} - GET transactions - NO TRANSACTIONS FOUND", f"from: {From_Date}\nto: {To_date}\naccount: {Account.IBAN}\nresponse: {res.text}")
                else:
                    print(f"[WARN] - {res.status_code} - GET transactions - error ", f"from: {From_Date}\nto: {To_date}\naccount: {Account.IBAN}\nresponse: {res.text}")
                    EmailObj.SendEmail(f"[WARN] - BOC RUN - {res.status_code} - GET transactions", f"from: {From_Date}\nto: {To_date}\naccount: {Account.IBAN}\nresponse: {res.text}")
                return 1
        elif (res.status_code>=500): ##Interal error
                EmailObj.SendEmail("[BOC - 500 - ERROR] - status_code "+Account.IBAN,res.text+" "+url)
                Account.to_update=0                   
                return 1       
            
        # self.get_balances(Account)

    def get_balances(self,Account):   
        if len(Account.account_type)==0:
            
            url= self.baseurl+'v1/accounts/'+Account.Account_id+'/balance'
            
            querystring = {
                "client_id":self.clinet_id,
                "client_secret":self.client_secret
            }

            payload = ""
            
            headers = {
                'Content-Type': "application/json",
                'Authorization': "Bearer "+self.OuathCode,
                'subscriptionId':Account.subscriptionId,
                'originUserId': Account.originid,
                'tppId': self.TPPID,
                'journeyId': "abc",
                'timeStamp': "1557748446",
                'cache-control': "no-cache"
            }
            
            res = requests.request("GET", url, data=payload, headers=headers, params=querystring) 
            
            if (res.status_code==200): 
                respond=json.loads(res.text)
                Balance=respond[0]['balances'] 
                Account.available_balance=float(Balance[0]['amount'])
                Account.Currency=respond[0]['currency']
                Account.current_balance=float(Balance[1]['amount'])
                Account.account_type=respond[0]['accountType']
            elif (res.status_code==401):
                EmailObj.SendEmail("[BOC - 401 - ERROR] - API Error code 401 in get_balances "+ str(datetime.today().strftime("%d/%m/%Y")),Account.IBAN)  
            else:
                print(f"[WARN] - {res.status_code} - GET Balance - {Account.Account_id} - {res.text}")

        # AM: 28-08-2023
        # if (Account.available_balance>Account.current_balance) or (Account.available_balance<Account.current_balance):                
        if Account.account_type in('PROFESSIONAL/BUSINESS LOANS', 'GUARANTEE DEPOSITS','CURRENT A/CS LOCAL-DCA','CARD ACCOUNTS','CURRENT A/CS-FOREIGN'):
            Account.bank_balance=Account.current_balance
        else:
            Account.bank_balance=Account.available_balance
            print(f"account: {Account.Account_id}\ntype: {Account.account_type}\navailable: {Account.available_balance}\ncurrent: {Account.current_balance}")
        # else:
        #     Account.bank_balance=Account.available_balance


######################################################################################################################################################
############################################################### ACCOUNT CLASS ########################################################################
######################################################################################################################################################
######################################################################################################################################################

class Account():
    def __init__(self,Organization,Company='',Account_id='',IBAN='',subscriptionId='',originid='', run_type='Balance'):
        self.Account_id=Account_id  
        self.bank_name='BOC'
        self.IBAN=IBAN
        self.Organization=Organization
        self.subscriptionId=subscriptionId
        self.originid=originid
        self.Company=Company
        self.Run_Dates=[]
        self.subscription_expire_date=''         
        self.DB_Obj=Db_request(self.Organization)
        self.next_seq=-1
        self.Raw_Transactions=[]
        self.balance=0
        self.Currency=''
        self.running_balance=0
        self.bank_balance=0
        self.current_balance=0
        self.available_balance=0
        self.start_balance=0
        self.end_balance=0
        self.final_Transactions=[]
        self.today_Transaction_amount=0
        self.row_count=0
        self.account_type=''
        self.run_type=run_type
        self.to_update=1

    def clear_data(self):
        self.__init__(self.Organization)

    def get_account_run_seq(self):
        (self.DB_Obj).DBRequest('select max(Run_Seq) from BOC_API_RUN_LIST where Account_id=?',[self.IBAN]) 
        seq=(self.DB_Obj).Results
        next_seq=int(seq[0][0])+1
        self.next_seq=next_seq

    def get_account_info(self):
        sql="select company, currency from accounts_info where Account_id=?"
        (self.DB_Obj).DBRequest(sql, [self.IBAN]) 
        res = (self.DB_Obj).Results
        if res is None or res == None:
            return '', ''
        else:
            return res[0][0], res[0][1]

    def update_account_att(self,account_att):
        self.Account_id=account_att[3]
        self.IBAN=account_att[4]
        self.subscriptionId=account_att[5]
        self.originid=account_att[2]
        self.Company, self.Currency = self.get_account_info()
        self.Company=account_att[1] if self.Company == '' else self.Company
        self.get_account_run_seq()
        self.get_account_balance()

    def get_account_balance(self):
        sql="select last_balance from BOC_API_RUN_LIST \
             where account_id=? and Type_='Transactions' and Run_Seq = (select max(Run_Seq) from BOC_API_RUN_LIST where account_id=? and Type_='Transactions') "
        sql="""
            select top(1) last_balance
            from boc_api_run_list
            where account_id=?
            order BY last_mod_date desc, run_seq desc    
            """
        # (self.DB_Obj).DBRequest(sql,[self.IBAN,self.IBAN]) 
        (self.DB_Obj).DBRequest(sql, [self.IBAN]) 
        Res=(self.DB_Obj).Results
        if (Res == None):
            self.balance=-99999999
        else :
            self.balance=float(Res[0][0])
        self.running_balance=self.balance

    def check_expration_date(self):
        (self.DB_Obj).DBRequest("select * from BOC_Activiation where originUserId=? and subscription_status='A' ",[self.originid]) 
        res=(self.DB_Obj).Results
        if res==None:
            self.subscription_expire_date=datetime.today().date()+timedelta(days=1)
        else:
            self.subscription_expire_date=datetime.strptime(res[0][4],'%Y-%m-%d').date()
           

    def check_curr_seq(self):       
        (self.DB_Obj).DBRequest("select curr_seq_id from  accounts_info where account_id=?",[self.IBAN]) 
        res=(self.DB_Obj).Results
        if  (res==None) :            
            self.insertnewaccount()  
            self.row_count=1
        else :              
             self.row_count=int(res[0][0])
             if self.validate_no_dupilcated_seq()==-1:
                    EmailObj.SendEmail("BOC has seuqance issue updating sequance"+self.IBAN,"")    
                    sqlupdate="update accounts_info  set curr_seq_id=max_seq+1 \
                         from accounts_info a,(select account_id,max(Transcation_seq) max_seq\
                         from banks_row_data   where Transcation_seq>? \
                         group by account_id) b   where a.account_id=b.account_id\
                         and a.bank_name='BOC'"
                    (self.DB_Obj).DBRequest(sqlupdate,[0])
                    (self.DB_Obj).DBRequest("select curr_seq_id from  accounts_info where account_id=?",[self.IBAN])
                    res=(self.DB_Obj).Results
                    self.row_count= int(res[0][0])
          

    def  insertnewaccount(self) :
        if len(self.Company)>0:
            self.Company=self.Remove_LTD(self.Company)
            if len(self.Company.split())==1:
                    self.Company=Text_serivce([' '.join(New_Company.split())]).Replace_strings()
            else: 
                    self.Company=Text_serivce(New_Company.split()).Replace_strings()
            self.Company=' '.join(self.Company)
            self.Company=MakeTitle(self.Company)
        else:
            self.Company='Unknown'
        args.append((self.IBAN,self.bank_name,self.Currency,self.Company))   
        (self.DB_Obj).DBRequest("insert into accounts_info values  ( ?,?,?,?,sysdatetime(),1,0,1,0,'Private')",args)
        return 1

    def validate_no_dupilcated_seq(self):
        sql='select count(*) from banks_row_data \
             where Transcation_seq>0 and Account_ID=?  and Transcation_seq>=? '        
        (self.DB_Obj).DBRequest(sql,[self.IBAN,self.row_count])
        res=(self.DB_Obj).Results       
        if (res==None):
            return 0
        elif int(res[0][0])>0:
            return -1

    def update_account_info(self):
        if self.row_count>0:
          (self.DB_Obj).DBRequest('update accounts_info set curr_seq_id=? where account_id= ?',[self.row_count,self.IBAN])
  
    def update_BOC_API_Refernce_table(self,today_trans_total=''):
        sql="insert into BOC_API_RUN_LIST values ((NEXT VALUE FOR BOC_API_RUN_SEQ),?,?,?,?,?,?,?,sysdatetime(),?)"
        
        args = [
            self.originid, self.IBAN, self.run_type, self.Run_Dates[0], self.Run_Dates[1], len(self.final_Transactions), self.next_seq, self.running_balance
        ]
        
        (self.DB_Obj).DBRequest(sql,args)
        
        # if abs(round((self.running_balance-self.bank_balance),2))>0:
        #     (self.DB_Obj).DBRequest('delete from API_ACCOUNTS_CONTROL where Account_id=?',[self.IBAN])
        #     sqlinsert="insert into API_ACCOUNTS_CONTROL values (?,?,?,?,?,?,sysdatetime())"
        #     (self.DB_Obj).DBRequest(sqlinsert,[self.IBAN,self.Company,self.running_balance,self.bank_balance,self.running_balance-self.bank_balance,today_trans_total[1]])


######################################################################################################################################################
############################################################### OPERATIONAL CLASS ####################################################################
######################################################################################################################################################
######################################################################################################################################################
 
class Operational():
    
    def __init__(self,Organization):
        self.Account_list_for_run=[]
        self.Organization=Organization
        self.DB_Obj=Db_request(self.Organization)
        self.num_of_diff_records=0
        self.control_list_balance=[]
        self.ftms_list_of_trnas=[]
        self.first_missing_records_date=''
        self.api_run_table=[]
        self.account_type_in_date=''
        self.num_of_reocrds_in_date=0
         

    #def get_account_list(self):##Get active accounts in BOC API service from the accounts table 
    #       (self.DB_Obj).DBRequest('delete from API_ACCOUNTS_CONTROL') 
    #       sql="select * from BOC_API_ACC_List where  account_status='A'"
    #       (self.DB_Obj).DBRequest(sql,[]) 
    #       Account_list=(self.DB_Obj).Results
    #       if not(Account_list==None):
    #           self.Account_list_for_run=Account_list
    
               
    def get_account_list(self) :
        (self.DB_Obj).DBRequest('delete from  API_ACCOUNTS_CONTROL')
        sql="select * from BOC_API_ACC_List where  account_status='A'"
        (self.DB_Obj).DBRequest(sql,[])
        Account_list=(self.DB_Obj).Results
        if not(Account_list==None):
            self.Account_list_for_run=Account_list





    def CalcRunDates(self,Account):##From the last run day+1 , till yesterday
       sql="select To_Date from BOC_API_RUN_LIST where account_id=? and Run_Seq in (select max(Run_Seq) from BOC_API_RUN_LIST where account_id=?)"
       (self.DB_Obj).DBRequest(sql,[Account.IBAN,Account.IBAN]) 
       res=(self.DB_Obj).Results
       From_date=datetime.strptime(res[0][0],'%Y-%m-%d').date()+timedelta(days=1)
       To_date=datetime.today().date()-timedelta(days=1)
       if To_date>(From_date):
            Account.Run_Dates=[From_date,To_date]
            return [From_date,To_date]
       elif To_date==(From_date):
            Account.Run_Dates=[To_date,To_date]
            return [To_date,To_date]
       else:
            Account.Run_Dates=[]
            return []

    def process_transactions(self,Account):
        if Account.to_update==0:
            return 0
        New_Transaction=Transaction()
        New_Transaction.IBAN=Account.IBAN
        New_Transaction.file_name='BOCAPI'+str(datetime.today().date()).replace('-','') ##File name convention 
        New_Transaction.Company=Account.Company
        Account.final_Transactions=[]
        if len(Account.Raw_Transactions)>0:    ##If there were transactions in the dates
            Account.get_account_balance()     ##Since no running balance on transactions need to get the last balance
            Account.check_curr_seq()  ##get sequance
            New_Transaction.row_count=Account.row_count
            for Rec in list(reversed(Account.Raw_Transactions)): ##BOC API return the transaction from new to old                     
                New_Transaction.Transaction_Date=pandas.to_datetime( Rec['postingDate'],format="%d/%m/%Y")  
                New_Transaction.Description=Rec['description']                   
                New_Transaction.Credit_Debit(float(Rec['transactionAmount']['amount'] or 0),Rec['dcInd'])
                New_Transaction.Currency=Rec['transactionAmount']['currency']            
                New_Transaction.Set_Trasnaction_type(Rec['description'])
                New_Transaction.GetSuppliername() ##Extracting supplier name from description
                Account.running_balance+=New_Transaction.Credit-New_Transaction.Debit
                
                Account.running_balance = round(Account.running_balance, 2)

                if 'runningBalance' in Rec and Account.running_balance != Rec['runningBalance']:
                    print(f'BALANCE NOT MATCHED WITH RUNNING BALANCE OF TRANSACTION - \nrunning balance: {Account.running_balance}\ntransaction balance: {Rec["runningBalance"]}')
                    Account.running_balance = Rec['runningBalance']

                New_Transaction.Balance=Account.running_balance 
                
                Account.final_Transactions.append(New_Transaction.create_transaction())
                New_Transaction.row_count+=1
            
            if round(Account.running_balance, 2) != Account.end_balance:
                print(f'[WARN] - ACCOUNT: {Account.IBAN} - RUNNING BALANCE {Account.running_balance} NOT MATCHED WITH ACCOUNT END BALANCE {Account.end_balance}')

            Account.row_count=New_Transaction.row_count
        
        ##if no tranasctions only balance update
        elif len(Account.Raw_Transactions)==0 and len(Account.Run_Dates)>0: 
            if Account.running_balance == -99999999:
                Account.get_account_balance() 
            # New_Transaction.Transaction_Date=datetime.today().date()
            New_Transaction.Transaction_Date=datetime.today().date()-timedelta(days=1)
            New_Transaction.Description='Balance Update Only'
            New_Transaction.Debit=0
            New_Transaction.Credit=0
            New_Transaction.Currency=Account.Currency
            New_Transaction.Trnasction_type=''
            New_Transaction.Balance=Account.balance
            New_Transaction.row_count=0
            Account.final_Transactions.append(New_Transaction.create_transaction())
        
    def fix_run_seq(self) :
        sql="""
            select 
                a.*, DATEDIFF(Day, from_date, to_date) 
            from 
                boc_api_run_list a
            where 
                Run_Seq>=? and DATEDIFF(Day, from_date, to_date) > 0
            """
        
        (self.DB_Obj).DBRequest(sql,[270]) 
        accounts_to_check=(self.DB_Obj).Results
        
        if accounts_to_check==None:
            return 0
        
        for account in accounts_to_check:
            from_date=datetime.strptime(account[4],'%Y-%m-%d').date() 
            to_date=datetime.strptime(account[5],'%Y-%m-%d').date()  
            run_seq=int(account[7])
            while from_date<=to_date:
                self.api_run_table.append(self.create_api_table_record((account[1],account[2],from_date,from_date,run_seq)))
                run_seq=run_seq+1
                from_date+=timedelta(days=1)
            self.get_run_attribute()
            self.update_api_db(account[7])

        return 1

###############################################################################################################################
    def FIX_BLUELACE_NEWSIGHT_BALANCE(self):
        try :
            accountsToFix=['CY73 00200 1950 0003 5703 165 5159','CY73 0020 0195 0000 3570 3381 3118','CY37 0020 0195 0000 3570 3165 4837']
            for accToFix in accountsToFix:
                # Getting first ALL today Transactions for this account (if exist)
                sql="select * from banks_row_data where Account_ID=?  \
                        and MONTH(last_mod_date)=MONTH(SYSDATETIME()) and DAY(last_mod_date)=DAY(SYSDATETIME())  \
                        and YEAR(last_mod_date)=YEAR(SYSDATETIME()) and Transcation_seq>0 \
                        order by Transcation_seq asc"
                (self.DB_Obj).DBRequest(sql,[accToFix]) 
                today_transaction_to_check=(self.DB_Obj).Results

                if today_transaction_to_check==None:
                    print("No New Transaction Today for: "+accToFix)
                    EmailObj.SendEmail("[BOC] - NO Transaction for "+accToFix+" account",'')   

                    # Update boc_api_run_list balance - Based on Today Balance
                    sql="update boc_api_run_list set last_balance= \
                        (select distinct(balance) from banks_row_data where  Account_ID=?  \
                            and MONTH(last_mod_date)=MONTH(SYSDATETIME()) and DAY(last_mod_date)=DAY(SYSDATETIME())  \
                            and YEAR(last_mod_date)=YEAR(SYSDATETIME()) and filename like '%BOCAPI%') \
                        where MONTH(last_mod_date)=MONTH(SYSDATETIME()) and DAY(last_mod_date)=DAY(SYSDATETIME())  \
                        and YEAR(last_mod_date)=YEAR(SYSDATETIME()) and account_id=? and run_seq=(select MAX(run_seq) from boc_api_run_list where account_id=?) "
                    (self.DB_Obj).DBRequest(sql,[accToFix,accToFix,accToFix]) 
                    status=(self.DB_Obj).Results

                    print ("Finish fix "+accToFix+" balance only @BOC_API_RUN_LIST based on today Balance")
                    EmailObj.SendEmail("[BOC] - Finish fix "+accToFix+" balance only @BOC_API_RUN_LIST based on today Balance",'')   


                else : #if there are NEW transaction today
                    # Getting the latest balance BEFORE today transactions (as a referrence point that from there we will star calculate) :
                        # first we will try to see the balance of the transaction that has one sequence down , then todat Minimum transaction seq
                    EmailObj.SendEmail("[BOC] - There are NEW Transaction for "+accToFix+" account",'')   
                    sql="SELECT distinct balance from banks_row_data                                                                   \
                         WHERE                                                                                                          \
                             Transcation_seq+1=(select MIN(Transcation_seq) from banks_row_data where Account_ID=?                       \
                                                and MONTH(last_mod_date)=MONTH(SYSDATETIME()) and DAY(last_mod_date)=DAY(SYSDATETIME())   \
                             and YEAR(last_mod_date)=YEAR(SYSDATETIME()) and Transcation_seq>0) and account_id=? and Transcation_seq>0"
                    (self.DB_Obj).DBRequest(sql,[accToFix, accToFix]) 
                    prevBalance=(self.DB_Obj).Results[0][0]
                        # if there were not transactions (new month for example) , then we will refer to the balance that was set yesterday as  "balance update Only"
                    if prevBalance==None:
                        sql="select distinct balance from banks_row_data where Account_ID=?  \
                                and MONTH(last_mod_date)=MONTH(SYSDATETIME()) and DAY(last_mod_date)=DAY(SYSDATETIME())-1  \
                                and YEAR(last_mod_date)=YEAR(SYSDATETIME()) and Transcation_seq=0"
                        (self.DB_Obj).DBRequest(sql,[accToFix]) 
                        prevBalance=(self.DB_Obj).Results[0][0]
            
                    #getting Min(Transcation_seq) and Max(Transcation_seq) so we can go over the transaction from Min to Max and Update the balance accordingly
                    sql="select MIN(Transcation_seq) , MAX(Transcation_seq) from banks_row_data where Account_ID=?  \
                        and MONTH(last_mod_date)=MONTH(SYSDATETIME()) and DAY(last_mod_date)=DAY(SYSDATETIME())  \
                        and YEAR(last_mod_date)=YEAR(SYSDATETIME()) and Transcation_seq>0"
                    (self.DB_Obj).DBRequest(sql,[accToFix]) 
                    min_max_transaction_seq=(self.DB_Obj).Results
            
                    min_seq=min_max_transaction_seq[0][0]
                    max_seq=min_max_transaction_seq[0][1]
                    seq=min_seq

                    for trx in today_transaction_to_check:
                        if seq==min_seq :  # meaning that this is the first transaction we need to update the balance for (we will reffer to the balance from yesterday)
                                argsTrx=[accToFix,seq]
                                sql="select distinct debit from banks_row_data  \
                                                                 where Account_ID=?  \
                                                                 and MONTH(last_mod_date)=MONTH(SYSDATETIME()) \
                                                                 and DAY(last_mod_date)=DAY(SYSDATETIME())  \
                                                                 and YEAR(last_mod_date)=YEAR(SYSDATETIME()) \
                                                                 and Transcation_seq=?"
                                (self.DB_Obj).DBRequest(sql,argsTrx) 
                                debit=(self.DB_Obj).Results[0][0]
                                sql="select distinct fees from banks_row_data  \
                                                                 where Account_ID=?  \
                                                                 and MONTH(last_mod_date)=MONTH(SYSDATETIME()) \
                                                                 and DAY(last_mod_date)=DAY(SYSDATETIME())  \
                                                                 and YEAR(last_mod_date)=YEAR(SYSDATETIME()) \
                                                                 and Transcation_seq=?"
                                (self.DB_Obj).DBRequest(sql,argsTrx) 
                                fees=(self.DB_Obj).Results[0][0]
                                sql="select distinct credit from banks_row_data  \
                                                                 where Account_ID=?  \
                                                                 and MONTH(last_mod_date)=MONTH(SYSDATETIME()) \
                                                                 and DAY(last_mod_date)=DAY(SYSDATETIME())  \
                                                                 and YEAR(last_mod_date)=YEAR(SYSDATETIME()) \
                                                                 and Transcation_seq=?"
                                (self.DB_Obj).DBRequest(sql,argsTrx) 
                                credit=(self.DB_Obj).Results[0][0]

                            
                                newBalance=float(18.18)  # No reason for this number...it just for allocate the parameter as float
                                newBalance=float(prevBalance-debit-fees+credit)
                                argsBB=[newBalance,accToFix,seq] 
                                sqlUpdateBB = "update banks_row_data set balance=? where Account_ID=? and Transcation_seq=?"
                                (self.DB_Obj).DBRequest(sqlUpdateBB,argsBB)
                                res=(self.DB_Obj).Results
                                seq=seq+1
                        else :  # meaning that we are on the second transaction and above (we will reffer to the balance of (transaction_seq-1)
                            if seq<=max_seq :
                                argsTrx=[accToFix,seq]
                                sql="select distinct balance from banks_row_data  \
                                                                where Account_ID=?  \
                                                                and MONTH(last_mod_date)=MONTH(SYSDATETIME()) \
                                                                and DAY(last_mod_date)=DAY(SYSDATETIME())  \
                                                                and YEAR(last_mod_date)=YEAR(SYSDATETIME()) \
                                                                and Transcation_seq=?-1"
                                (self.DB_Obj).DBRequest(sql,argsTrx) 
                                prevBalance=(self.DB_Obj).Results[0][0]
                                sql="select distinct debit from banks_row_data  \
                                                                 where Account_ID=?  \
                                                                 and MONTH(last_mod_date)=MONTH(SYSDATETIME()) \
                                                                 and DAY(last_mod_date)=DAY(SYSDATETIME())  \
                                                                 and YEAR(last_mod_date)=YEAR(SYSDATETIME()) \
                                                                 and Transcation_seq=?"
                                (self.DB_Obj).DBRequest(sql,argsTrx) 
                                debit=(self.DB_Obj).Results[0][0]
                                sql="select distinct fees from banks_row_data  \
                                                                 where Account_ID=?  \
                                                                 and MONTH(last_mod_date)=MONTH(SYSDATETIME()) \
                                                                 and DAY(last_mod_date)=DAY(SYSDATETIME())  \
                                                                 and YEAR(last_mod_date)=YEAR(SYSDATETIME()) \
                                                                 and Transcation_seq=?"
                                (self.DB_Obj).DBRequest(sql,argsTrx) 
                                fees=(self.DB_Obj).Results[0][0]
                                sql="select distinct credit from banks_row_data  \
                                                                 where Account_ID=?  \
                                                                 and MONTH(last_mod_date)=MONTH(SYSDATETIME()) \
                                                                 and DAY(last_mod_date)=DAY(SYSDATETIME())  \
                                                                 and YEAR(last_mod_date)=YEAR(SYSDATETIME()) \
                                                                 and Transcation_seq=?"
                                (self.DB_Obj).DBRequest(sql,argsTrx) 
                                credit=(self.DB_Obj).Results[0][0]


                                newBalance=float(18.18)  # No reason for this number...it just for allocate the parameter as float
                                newBalance=float(prevBalance-debit-fees+credit)
                                argsBB=[newBalance,accToFix,seq] 
                                sqlUpdateBB = "update banks_row_data set balance=? where Account_ID=? and Transcation_seq=?"
                                (self.DB_Obj).DBRequest(sqlUpdateBB,argsBB)
                                res=(self.DB_Obj).Results
                                seq=seq+1
                            else :
                                break


                                # Update boc_api_run_list balance - Based on Today Balance
                    sql="update boc_api_run_list  \
                         set last_balance=        \
                                           (select distinct(balance) from banks_row_data     \
                                                    where Account_ID=?                        \
                                                            and MONTH(last_mod_date)=MONTH(SYSDATETIME())   \
                                                            and DAY(last_mod_date)=DAY(SYSDATETIME())       \
                                                            and YEAR(last_mod_date)=YEAR(SYSDATETIME())     \
                                                            and Transcation_seq=                            \
                                                                                (select MAX(Transcation_seq) \
                                                                                 from banks_row_data where account_id=?)) \
                        where MONTH(last_mod_date)=MONTH(SYSDATETIME()) and DAY(last_mod_date)=DAY(SYSDATETIME())  \
                              and YEAR(last_mod_date)=YEAR(SYSDATETIME()) and account_id=?                        \
                              and run_seq=(select MAX(run_seq) from boc_api_run_list where account_id=?) "
                    (self.DB_Obj).DBRequest(sql,[accToFix,accToFix,accToFix,accToFix]) 
                    status=(self.DB_Obj).Results

                    EmailObj.SendEmail("[BOC] - Finish fix "+accToFix+" balance on BANKS_ROW_DATA && BOC_API_RUN_LIST based on today Balance",'')   
                    print ("Finish fix "+accToFix+" balance on BANKS_ROW_DATA && BOC_API_RUN_LIST based on today Balance")

            return 0
        except Exception as e:
            print(str(sys.exc_info()[0])+" : "+str(e.args[0]))
            EmailObj.SendEmail("[BOC - ERROR] - FAILED with fixing balance on based on today Balance",'')   
            return 1
###############################################################################################################################
    def update_api_db(self,run_seq):
         sqlupdate="update BOC_API_RUN_LIST set run_seq=9999   where run_seq=? and account_id=?"
         (self.DB_Obj).DBRequest(sqlupdate,[run_seq,self.api_run_table[0][1]])
         sqlinsert="insert into BOC_API_RUN_LIST values ( (NEXT VALUE FOR BOC_API_RUN_SEQ),?,?,?,?,?,?,?,sysdatetime(),?)"
         (self.DB_Obj).DBRequest(sqlinsert,self.api_run_table)
         (self.DB_Obj).DBRequest('delete from BOC_API_RUN_LIST where run_seq=9999 and account_id=?',[self.api_run_table[0][1]])
         self.api_run_table[:]=[]
    
    def get_run_attribute(self):
        self.api_run_table=[list(row) for row in self.api_run_table]
        from_date=self.api_run_table[0][3]
        to_date=self.api_run_table[len(self.api_run_table)-1][3]
        Acc_id=self.api_run_table[0][1]
        index=0
        sql="select distinct(balance) from banks_row_data \
            where Transcation_seq=(select max(Transcation_seq) from banks_row_data where booking_Date<=? \
            and account_id=?)   and  account_id=?  "
        (self.DB_Obj).DBRequest(sql,[from_date,Acc_id,Acc_id]) 
        last_balance=(self.DB_Obj).Results
        if last_balance==None : ##first run:
            last_balance=0
        if len(str(last_balance))>1 or last_balance==0:
            sql="select distinct(balance) from banks_row_data \
            where booking_date=(select max(booking_date) from banks_row_data where booking_Date<=? \
            and account_id=?)   and  account_id=?"
            (self.DB_Obj).DBRequest(sql,[from_date,Acc_id,Acc_id]) 
            last_balance=(self.DB_Obj).Results
       
        last_balance=float(last_balance[0][0])
        sql="select booking_date,count(*) from banks_row_data \
             where booking_Date>=? and booking_date<=?\
             and account_id=? and Transcation_seq>0 \
             group by booking_date order by booking_date"
        (self.DB_Obj).DBRequest(sql,[from_date,to_date,Acc_id]) 
        account_records=(self.DB_Obj).Results
        for record in self.api_run_table :
          if account_records==None:
             if self.api_run_table[index][2]=='Unknown':
                     self.api_run_table[index][2]='Balance'
                     self.api_run_table[index][5]=1
                     self.api_run_table[index][7]=last_balance
                     index+=1
                     continue
          else:
             for rec in account_records:
                 if record[3]==datetime.strptime(rec[0],'%Y-%m-%d %H:%M:%S').date():
                     self.api_run_table[index][2]='Transactions'
                     self.api_run_table[index][5]=rec[1]
                     self.api_run_table[index][7]=self.Get_balance(Acc_id,datetime.strptime(rec[0],'%Y-%m-%d %H:%M:%S').date())
                     last_balance=float((self.api_run_table[index][7]))                     
             if self.api_run_table[index][2]=='Unknown':
                     self.api_run_table[index][2]='Balance'
                     self.api_run_table[index][5]=1
                     self.api_run_table[index][7]=last_balance
             index+=1




    def Get_balance(self,Acc_id,from_date):
         sql="select balance from banks_row_data \
            where Transcation_seq=(select max(Transcation_seq) from banks_row_data where booking_Date=? \
            and account_id=?)   and  account_id=? and booking_Date=?"
         (self.DB_Obj).DBRequest(sql,[from_date,Acc_id,Acc_id,from_date]) 
         max_balance=(self.DB_Obj).Results
         return float(max_balance[0][0])

    def create_api_table_record(self,account):
        return ((account[0],account[1],'Unknown',account[2],account[3],0,account[4],0))


    def update_DB(self,Account):
        if len(Account.final_Transactions)>0:
            (self.DB_Obj).DBRequest("insert into banks_row_data values  (NEXT VALUE FOR bank_rec_id,?,?,?,?,?,?,?,?,?,?,?,sysdatetime(),null,?,?,?)",Account.final_Transactions)
            Account.update_account_info()
            Account.update_BOC_API_Refernce_table(self.control_list_balance)

    def find_missing_records(self,New_Call,Account):
        if abs(round((Account.running_balance-Account.bank_balance),2))>0:  
            if round(abs(round((Account.running_balance-Account.bank_balance),2))-abs(round(Account.today_Transaction_amount,2)),2)==0:
                return 0
            Run_Dates=[datetime.today().date()-timedelta(days=10),datetime.today().date()-timedelta(days=1)]
            New_Call.get_Transactions(Run_Dates,Account)
            sql="select * from banks_row_data where Transcation_seq>0 and booking_date>=? and account_id=? order by Transcation_seq"
            (self.DB_Obj).DBRequest(sql,[Run_Dates[0],Account.IBAN]) 
            res=(self.DB_Obj).Results
            if res==None:
                 self.ftms_list_of_trnas=[]
            else:
                self.ftms_list_of_trnas=res
            if (len(self.ftms_list_of_trnas)<len(Account.Raw_Transactions)):       
                self.process_transactions(Account)              
                self.check_first_missing_record(Account)
                if self.first_missing_records_date>=datetime.today().date()-timedelta(days=10):
                    Run_orchestror=Operational(self.Organization)
                    Account.Run_Dates[0]=self.first_missing_records_date
                    self.find_api_date(Account.IBAN)
                    Run_orchestror.process_transactions(Account)##Process transactions              
                    Run_orchestror.run_control(New_Call,Account)
                    Run_orchestror.update_DB(Account)
    
    def find_api_date(self,IBAN):
            sql="select min(Run_Seq) from boc_api_run_list where from_date=? and account_id=?"
            (self.DB_Obj).DBRequest(sql,[self.first_missing_records_date,IBAN]) 
            res=(self.DB_Obj).Results
            seq_to_del=int(res[0][0] or 0)
            if seq_to_del==None:
                stop=1##Accounts need to be fix manauly
            if seq_to_del>0:
                (self.DB_Obj).DBRequest('delete from boc_api_run_list where account_id=? and Run_Seq>=?',[IBAN,seq_to_del])
                (self.DB_Obj).DBRequest('delete from banks_row_data where account_id=? and booking_date>=?',[IBAN,self.first_missing_records_date])
    
    def check_first_missing_record(self,Account):
        for Rec in Account.final_Transactions:
            TransAtt=[Rec[0],Rec[1],Rec[2],Rec[3],Rec[4],Rec[5]]
            if len(self.ftms_list_of_trnas)==0:
                self.first_missing_records_date=TransAtt[0].date()
                return 0
            for FTMSTrans in self.ftms_list_of_trnas:
             if FTMSTrans[1]==TransAtt[0]:  ##Date is the same
                if FTMSTrans[2]==TransAtt[1]: ##Description is the same
                    if  FTMSTrans[3]==TransAtt[2] : ##Debit is the same
                        if  FTMSTrans[4]==TransAtt[3] : ##Credit is the same
                                continue                         
                        else:
                            self.first_missing_records_date=TransAtt[0].date()
                            return 0
                    else: 
                          self.first_missing_records_date=TransAtt[0].date()
                          return 0
                else:
                     self.first_missing_records_date=TransAtt[0].date()
                     return 0
             else:
                self.first_missing_records_date=TransAtt[0]  .date()
                return 0
        if len(str(self.first_missing_records_date))==0:
            self.first_missing_records_date=datetime.today().date()-timedelta(days=365)

    def run_control(self,New_Call,Account):
        total_balance=0
        if abs(round((Account.running_balance-Account.bank_balance),2))>0:            
            self.control_list_balance=[]
            Run_Dates=[datetime.today().date(),datetime.today().date()]
            New_Call.get_Transactions(Run_Dates,Account)
            if len(Account.Raw_Transactions)>0:
                for Rec in list(reversed(Account.Raw_Transactions)): ##BOC API return the transaction from new to old                             
                    Debit_Credit=Rec['dcInd']
                    Amount=float(Rec['transactionAmount']['amount'] or 0)
                    if Debit_Credit=='D' :
                        total_balance+=-Amount      
                    else:
                        total_balance+=Amount 
                Account.today_Transaction_amount=total_balance     
                self.control_list_balance.extend((Account.IBAN,total_balance))
           
            else:
                self.control_list_balance.extend((Account.IBAN,0))
           



######################################################################################################################################################
############################################################### TRANSACTION CLASS ####################################################################
######################################################################################################################################################
######################################################################################################################################################
    
class Transaction():
    def __init__(self):
        self.Account_list_for_run=[]
        self.Transaction_Date=None
        self.Description=''
        self.Debit=0
        self.Credit=0
        self.Fees=0
        self.Balance=0
        self.Currency=''
        self.Company=''
        self.IBAN=''
        self.Bank_name='BOC'
        self.row_count=0
        self.file_name=''
        self.Trnasction_type=''
        self.Supplier_name=''

    def create_transaction(self):            
        return  (self.Transaction_Date,self.Description,self.Debit,self.Credit,self.Fees,self.Balance,self.Currency,self.Company,self.IBAN,self.Bank_name,self.row_count,self.file_name,self.Trnasction_type,self.Supplier_name)

    def Credit_Debit(self,Amount,Debit_Credit):
        if Debit_Credit=='D' :
            self.Debit=Amount       
            self.Credit=0
        else :                
            self.Credit=Amount
            self.Debit=0

    def Set_Trasnaction_type(self,Trasnaction_type):
        self.Trnasction_type=Trasnaction_type
        if Trasnaction_type is None:
            self.Trnasction_type=''
        else :
            if 'foreign purchase' in self.Description.lower():
                self.Trnasction_type='Card Purchase - Foreign'
            elif len(set( ['purchase','card'] ).intersection(set( (self.Description.lower()).split())))>0:
                self.Trnasction_type='Credit Card Purchase'   
            elif 'cardtxnadmin' in ''.join(self.Description.lower().split()):
                self.Trnasction_type='Credit Card admin fees'
            elif 'cash payment bank' in self.Description.lower():
                self.Trnasction_type='Cash Payment Bank'
            elif 'credit voucher-p' in self.Description.lower():
                self.Trnasction_type='Credit Voucher-Purchase Return'
            else :
                self.Trnasction_type=''

    def GetSuppliername(self):##to check if supllier is set to ''
        self.Supplier_name=''
        List_of_words=['eur','gbp','usd','uah','auth','trace','ils','visa','lu','jcc','cy','gb','purchase']
        

        Word_to_remove_list = re.compile(r'\b(?:{0})\b'.format('|'.join(List_of_words)),re.IGNORECASE)
        if (self.Trnasction_type=='Commission - Fee') or ('charges our our ref' in self.Description.lower()) or ('cardtxn admin' in self.Description.lower()):
            self.Supplier_name='Bank charges'

        
        elif self.Trnasction_type=='Card Purchase - Foreign':
            self.Supplier_name=self.Description[40:len(self.Description)]
            
        elif self.Trnasction_type=='Credit Card Purchase':
            self.Supplier_name=self.Description[32:len(self.Description)]
            self.Supplier_name=Text_serivce(self.Supplier_name).remove_unwanted_words(List_of_words)    
            
        elif self.Trnasction_type=='Cash Payment Bank':
            self.Supplier_name==self.Description[30:len(self.Description)]
            
        elif self.Trnasction_type=='Credit Voucher-Purchase Return':
            self.Supplier_name=self.Description[50:len(self.Description)]

        elif self.Trnasction_type in ('Card Purchase - Local','Other Credit','Other Debit'):
            findindex=(self.Description.lower()).find('trace')
            if not(findindex)==-1:             
                self.Supplier_name=self.Description[findindex+6:len(self.Description)]
            
        elif self.Trnasction_type=='BOC Transfer' :             
            findindex=(str(self.Description).lower()).find('to')
            findindex2=(str(self.Description).lower()).find('a/c',findindex+1)
            if not(findindex==-1 or findindex2==-1):                         
                self.Supplier_name=self.Description[findindex+3:len(self.Description)]
            else:
                findindex=(str(self.Description).lower()).find('from')
                if not(findindex==-1 ):                         
                    self.Supplier_name=self.Description[findindex+4:len(self.Description)]
        elif self.Trnasction_type=='ATM Cash Withdrawal' : 
            self.Supplier_name='ATM Cash Withdrawal'
        elif self.Trnasction_type=='Transfer to Other Banks - Inward' :      
            findindex=self.Description.lower().find('by')
            findindex2=self.Description.lower().find('>',findindex)      
            if not(findindex==-1 or findindex2==-1):                    
                self.Supplier_name=self.Description[findindex+3:findindex2]
            elif findindex>0:
                self.Supplier_name=self.Description[findindex+3:len(self.Description)]                    
        
        else:
            FindIndex1=self.Description.find("to",0)
            FindIndex2=self.Description.find("a/c",FindIndex1) 
            if not(FindIndex1==-1 or FindIndex2==-1):                
                    self.Supplier_name=str(self.Description[FindIndex1+2:FindIndex2-1]).strip()
        if not(self.Supplier_name=='Bank charges'):
            self.Supplier_name=Text_serivce(self.Supplier_name).remove_unwanted_words(List_of_words)
            self.Supplier_name=Text_serivce(self.Supplier_name).MakeTitle()
              

######################################################################################################################################################
############################################################### TEXT SERVICES CLASS ##################################################################
######################################################################################################################################################
######################################################################################################################################################
class Text_serivce():
    def __init__(self,Str_in='',Text_out=''):
        self.Text_in=Str_in
        self.word_list =['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec','one','two','three','four','five','six','seven','eight','nine','ten',' \
              eleven','twelve','thirteen','fourteen','fifteen','sixteen','seventeen', \
              'eighteen','nineteen','twenty','thirty','forty','fifty','sixty','seventy','eighty', \
              'ninety','hundred','thousand','monday','tuesday','wednesday','thursday','friday','saturday','sunday','january','february','march','april','may','june','july','august','september', \
                  'october','november','december','year','day','week','month','credit','debit','ftoacy'] 
        
        
  
    def remove_unwanted_words(self,list_of_words):       
        punctuation=re.compile(r'[-.?!,:;()/\@#$%^&*`+"<>|0-9]',re.IGNORECASE) 
        Word_to_remove_list = re.compile(r'\b(?:{0})\b'.format('|'.join(self.word_list+list_of_words)),re.IGNORECASE)
        name=punctuation.sub(" ",self.Text_in) 
        if len(name)>0 :
          name=Word_to_remove_list.sub(" ",name) 
        else:
          return self.remove_whit_space(name)       
        return self.remove_whit_space(name)

    def remove_whit_space(self,Str):
        return ' '.join(Str.split())


    def MakeTitle(self):
        Str_list=(self.Text_in.lower()).split()
        String_to_return=[]
        for Name in Str_list:
            String_to_return.append(Name.title())
        return ' '.join(String_to_return)

    def Remove_LTD(self):
        company_words_to_remove=['ltd','limited','limit','sa','bv','gmbh','cv']
        Company_to_return=[]
        append_word=1
        for Comapny_word in  self.Text_in.split():
            for word in company_words_to_remove:
                if word==(Comapny_word.replace('.','').lower()):
                   append_word=0
            if append_word==1:
                Company_to_return.append(Comapny_word)
            append_word=1      
        return ' '.join(Company_to_return)

    def Replace_strings(self):
        Strings_to_replace=[['teddy','sagi'],['ts'],['teddy','sagy'],['teddy']]
        i=0
        count=0
        Word_to_check=self.Text_in
        New_Words_List=[]    
        for uw_string in Strings_to_replace:
          if (len(set(Word_to_check).intersection(set(uw_string))))==(len(uw_string)): 
            if (' '.join(Word_to_check)).find(' '.join(uw_string))>=0:
                New_Words_List=(' '.join(Word_to_check)).replace(' '.join(uw_string),'Teddy Sagi')
                return New_Words_List.split()
            else:
                New_Words_List=(' '.join(Word_to_check)).replace(' '.join(sorted(set(uw_string))),'Teddy Sagi')
            Word_to_check=New_Words_List.split()
        if len(New_Words_List)>0:
            return New_Words_List.split
        