#!/usr/bin/env python3
import sys
# import os

# if str(os.getcwd())[0].lower()=='c':
#     sitepackage = "C:\GLIS\LOCAL_ENV\site-packages"
#     Organization='GlobeInvest'
#     #Organization='GItest'
# else:
sitepackage = "d:\home\python364x86\lib\site-packages"
Organization='GlobeInvest'
#Organization='GItest'

sys.path.append(sitepackage) 


from sendemail_package.Sendemail import SendEmails
from BankServices  import *

from datetime import datetime

total_trans = 0
i=0
accoun_run=0
EmailObj=SendEmails()
# EmailObj = SendEmails('', '', ['alexandros.mina@globeinvest.com'])

if i==0:  
    EmailObj.SendEmail("BOC API started : "+str(datetime.now()),'')   
    
    New_Call=Bank_API()  ##Initiate the API
    New_Call.get_API_Token()##Get Acsess token 
    Run_orchestror=Operational(Organization)
    Run_orchestror.get_account_list()##Get the list of active accounts in boc API
    New_Account=Account(Organization)##Create an account object
    
    for Running_Account in Run_orchestror.Account_list_for_run :            
        New_Account.update_account_att(Running_Account) ##Update account parameters
        print("Account num "+str(accoun_run+1)+" IBAN="+New_Account.IBAN+" "+str(datetime.now()))     
        
        print(New_Account.Account_id)
        currency = New_Call.get_account_details(New_Account)
        if currency != None and New_Account.Currency != currency:
            print(f"[WARN] - mismatched currency for account id: {New_Account.Account_id} > update to: {currency}")     
        
        if not New_Call.get_subscription_details(sub_id=New_Account.subscriptionId, origin_id=New_Account.originid):
            EmailObj.SendEmail(
                f"[WARN] - Subscription details - Failed retrieving subscription from API - {datetime.now()}",
                f"account: {New_Account.Account_id}\nsubscription: {New_Call.subscription_id}\norigin: {New_Call.origin_user_id}"
            )  
            New_Account.clear_data()##Reset account parameters
            New_Call.get_API_Token()
            continue

        New_Call.get_Transactions(Run_orchestror.CalcRunDates(New_Account),New_Account) ##Get transactions per dates
        print("Get transactions per dates "+str(accoun_run+1)+" IBAN="+New_Account.IBAN+" "+str(datetime.now()))     
        Run_orchestror.process_transactions(New_Account)##Process transactions           
        print("Process transactions "+str(accoun_run+1)+" IBAN="+New_Account.IBAN+" "+str(datetime.now()))     
        # Run_orchestror.run_control(New_Call,New_Account)##check no missing records
        # print("check no missing records "+str(accoun_run+1)+" IBAN="+New_Account.IBAN+" "+str(datetime.now()))     
        Run_orchestror.update_DB(New_Account)##update the databse with the run results 
        print("update_DB "+str(accoun_run+1)+" IBAN="+New_Account.IBAN+" "+str(datetime.now()))     
        total_trans += len(New_Account.final_Transactions)
        # Run_orchestror.find_missing_records(New_Call,New_Account)##if control show mismatch try to find missing balances           
        # print("find_missing_records "+str(accoun_run+1)+" IBAN="+New_Account.IBAN+" "+str(datetime.now()))     
        New_Account.clear_data()##Rest account parameters
        print("clear_data() "+str(accoun_run+1)+" IBAN="+New_Account.IBAN+" "+str(datetime.now()))     
           
        if i==5:
            New_Call.get_API_Token()
            i=1
           
        i+=1
        accoun_run+=1
           
    #   Run_orchestror.fix_run_seq()
    # print ("FIX BLUELACE & NEWSIGHT BALANCE")
    # Run_orchestror.FIX_BLUELACE_NEWSIGHT_BALANCE()

    EmailObj.SendEmail("BOC API finished : " + str(total_trans) + " new transactions added - " + str(datetime.now()),'')  
 