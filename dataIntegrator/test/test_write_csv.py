import pandas as pd
import random
import time

def write_rating_highdensity():
    item_list= []
    for i in range(1, 100):
        row = []
        row.append(i)
        row.append('Oasys'+str(i))
        item_list.append(row)
    print(item_list)
    print(len(item_list))
    df = pd.DataFrame(item_list)
    df.columns=['item_id', 'item_title']
    df.to_csv(r'D:\workspace_python\practice\data\pandasTest\item_list.csv', index=False, header=None)

    user_list= []
    for i in range(1, 1000):
        row = []
        row.append(i)
        row.append('user'+str(i))
        user_list.append(row)
    print(user_list)
    print(len(user_list))
    df = pd.DataFrame(user_list)
    df.columns=['user_id', 'user_name']
    df.to_csv(r'D:\workspace_python\practice\data\pandasTest\user_list.csv', index=False, header=None)


    ratingList= []
    columnNames = ['user_id', 'item_id', 'rating', 'unix_timestamp']
    try:
        for userId in range(1, 1000):
            used_App_Id = []
            for appId in range(1, random.randint(1, 10)):
                #randomAppId = random.randint(0, 98)
                randomAppId = random.randint(30, 70)
                if (randomAppId in used_App_Id):
                    continue
                print("userId:"+ str(userId) +" appId:"+ str(appId) + " randomAppId:" + str(randomAppId))

                row = []
                row.append(userId)
                row.append(item_list[randomAppId][0])
                #row.append(random.randint(1,5))
                row.append(random.randint(4, 5))
                row.append(int(time.time()))
                #row.append(appList[randomAppId][1])
                ratingList.append(row)

                used_App_Id.append(randomAppId)
    except Exception as e:
        print(e)
    df = pd.DataFrame(ratingList)
    #df.columns=['user_id', 'item_id', 'rating', 'unix_timestamp','title']
    #df.to_csv(r'D:\workspace_python\practice\data\pandasTest\mydata.csv', index=False, header=True)
    df.columns=['user_id', 'item_id', 'rating', 'unix_timestamp']
    df.to_csv(r'D:\workspace_python\practice\data\pandasTest\rating_data.csv', index=False, header=None)

def write_rating_spares():
    item_list= []
    for i in range(1, 20):
        row = []
        row.append(i)
        row.append('Oasys'+str(i))
        item_list.append(row)
    print(item_list)
    print(len(item_list))
    df = pd.DataFrame(item_list)
    df.columns=['item_id', 'item_title']
    df.to_csv(r'D:\workspace_python\practice\data\pandasTest\item_list.csv', index=False, header=None)

    user_list= []
    for i in range(1, 100):
        row = []
        row.append(i)
        row.append('user'+str(i))
        user_list.append(row)
    print(user_list)
    print(len(user_list))
    df = pd.DataFrame(user_list)
    df.columns=['user_id', 'user_name']
    df.to_csv(r'D:\workspace_python\practice\data\pandasTest\user_list.csv', index=False, header=None)
    ratingList= []
    columnNames = ['user_id', 'item_id', 'rating', 'unix_timestamp']
    try:
        for userId in range(1, 100):
            used_App_Id = []
            for appId in range(1, random.randint(1, 3)):
                #randomAppId = random.randint(0, 98)
                randomAppId = random.randint(3,7)
                if (randomAppId in used_App_Id):
                    continue
                print("userId:"+ str(userId) +" appId:"+ str(appId) + " randomAppId:" + str(randomAppId))

                row = []
                row.append(userId)
                row.append(item_list[randomAppId][0])
                #row.append(random.randint(1,5))
                row.append(random.randint(4, 5))
                row.append(int(time.time()))
                #row.append(appList[randomAppId][1])
                ratingList.append(row)

                used_App_Id.append(randomAppId)
    except Exception as e:
        print(e)
    df = pd.DataFrame(ratingList)
    #df.columns=['user_id', 'item_id', 'rating', 'unix_timestamp','title']
    #df.to_csv(r'D:\workspace_python\practice\data\pandasTest\mydata.csv', index=False, header=True)
    df.columns=['user_id', 'item_id', 'rating', 'unix_timestamp']
    df.to_csv(r'D:\workspace_python\practice\data\pandasTest\rating_data.csv', index=False, header=None)


#write_rating_highdensity()
write_rating_spares()
