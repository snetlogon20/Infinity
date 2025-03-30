import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import pairwise_distances

np.set_printoptions(suppress=True)  # 取消科学计数法输出
pd.set_option('display.max_rows', None)  # 展示所有行
pd.set_option('display.max_columns', None)  # 展示所有列


def predict(scoredata, similarity, type='user'):
    # 基于物品得推荐
    if type == 'item':
        predt_mat = scoredata.dot(similarity) / np.array([np.abs(similarity).sum(axis=1)])
    elif type == 'user':
        # 计算用户评分值 减少用户评分高低习惯影响
        user_meanscorse = scoredata.mean(axis=1)
        score_diff = (scoredata - user_meanscorse.reshape(-1, 1))
        predt_mat = user_meanscorse.reshape(-1, 1) + similarity.dot(score_diff) / np.array(
            [np.abs(similarity).sum(axis=1)]).T
    return predt_mat


# 读取数据
try:
    print('step 1 读取数据')
    r_cols = ['user_id', 'item_id', 'rating', 'unix_timestamp']
    scoredata = pd.read_csv(r'D:\workspace_python\practice\data\pandasTest\rating_data.csv', sep=',',  names=r_cols, header=None)
    print('数据形状', scoredata.shape)

    r_cols = ['user_id', 'user_name']
    user_data = pd.read_csv(r'D:\workspace_python\practice\data\pandasTest\user_list.csv', sep=',',  names=r_cols, header=None)
    print('数据形状', user_data.shape)

    r_cols = ['item_id', 'item_name']
    item_data = pd.read_csv(r'D:\workspace_python\practice\data\pandasTest\item_list.csv', sep=',',  names=r_cols, header=None)
    print('数据形状', item_data.shape)
except Exception as e:
    print(e)

# 生成用户-物品评分矩阵
print('step2 生成 用户物品评分矩阵')
# dataByUserId=scoredata.groupby('user_id')
# print(len(dataByUserId))
# dataByMovieId=scoredata.groupby('item_id')
# print(len(dataByMovieId))

n_users = len(user_data)
n_items = len(item_data)
# n_users = 999#len(dataByUserId)
# n_items = 99#len(dataByMovieId)
# n_users = 9#len(dataByUserId)
# n_items = 9#len(dataByMovieId)

print("n_users:{} n_items:{}".format(n_users, n_items))

data_matrix = np.zeros((n_users, n_items))
for line in range(np.shape(scoredata)[0]):
    print("line{}".format(line))
    row = scoredata['user_id'][line] - 1
    print("row:" + str(row))
    col = scoredata['item_id'][line] - 1
    print("col" + str(col))
    score = scoredata['rating'][line]
    print("score" + str(score))
    data_matrix[row, col] = score
print('用户物品矩阵形状', data_matrix.shape)
df_data_matrix=pd.DataFrame(data_matrix)
df_data_matrix.to_csv(r'D:\workspace_python\practice\data\pandasTest\knn_df_data_matrix.csv', index=False, header=None)
# 计算相似度
print('step3 计算相似度')
user_similaritry = pairwise_distances(data_matrix, metric='cosine')
item_similarity = pairwise_distances(data_matrix.T, metric='cosine')
print('user similarity', user_similaritry.shape)
print('item similartity', item_similarity.shape)
# 进行相似度进行预测
print('step4 预测')
user_prediction = predict(data_matrix, user_similaritry, type='user')
item_prediction = predict(data_matrix, item_similarity, type='item')

df_user_prediction=pd.DataFrame(user_prediction)
df_user_prediction.to_csv(r'D:\workspace_python\practice\data\pandasTest\knn_df_user_prediction.csv', index=False, header=None)
df_item_prediction=pd.DataFrame(item_prediction)
df_item_prediction.to_csv(r'D:\workspace_python\practice\data\pandasTest\knn_df_item_prediction.csv', index=False, header=None)

print('step4.1.1')
print(user_prediction)
print(type(user_prediction))
print(user_prediction.shape)
print(item_prediction.shape)

# 显示推荐结果
print('step 5 显示推荐结果')
print('----------------')
print('ubcf预测形状', user_prediction.shape)
print('real answer\n', data_matrix[:5, 5])
print('预测结果: user_prediction\n', user_prediction)
print('ibcf预测形状', item_prediction.shape)
print('real answer\n', data_matrix[:5, :5])
print('预测结果: item_prediction\n', item_prediction)
# 性能评估
print('step 6 性能评估')
from sklearn.metrics import mean_squared_error
from math import sqrt


def rmse(predct, realNum):
    predct = predct[realNum.nonzero()].flatten()
    realNum = realNum[realNum.nonzero()].flatten()
    return sqrt(mean_squared_error(predct, realNum))


print('u-base mse=', str(rmse(user_prediction, data_matrix)))
print('m-based mse=', str(rmse(item_prediction, data_matrix)))

row_number = 0
for row in user_prediction:
    user_data_row = user_data.loc[user_data['user_id'] == row_number+1]
    user_name = user_data_row.iloc[0, :]['user_name']

    column_number = 0
    dict_cells = {}
    for cell in row:
        #print(str(column_number) + " " + str(cell))
        dict_cells[column_number] = cell
        column_number = column_number + 1
    sorted_items = sorted(dict_cells.items(), key=lambda x: x[1], reverse=True)
    #print("sorted_items:" + str(sorted_items))
    item_loop = 0
    for item in sorted_items:
        if item_loop >= 5:
            break

        item_data_row = item_data.loc[item_data['item_id'] == item[0]]
        item_title = item_data_row.iloc[0, :]['item_name']

        print("user_name: " + str(user_name) + ", item_loop:" + str(item_loop) + ", item: " + str(item[0]) + ", recommended: " + str(item[1]) + ": item_title: " + item_title)
        item_loop = item_loop + 1
    row_number = row_number + 1

# user_prediction_df = pd.DataFrame(user_prediction)
# user_prediction_df_with_format = user_prediction_df.style.background_gradient(cmap='Blues')
# user_prediction_df_with_format.to_html(r'D:\workspace_python\practice\data\pandasTest\user_prediction_df_with_format.html')
#
# writer = pd.ExcelWriter(r'D:\workspace_python\practice\data\pandasTest\user_prediction_df_with_format.xlsx')
# user_prediction_df_with_format.to_excel(writer, index=False)
# writer.save()

user_name = user_data['user_name'].tolist()
item_name = item_data['item_name'].tolist()
user_prediction_df = pd.DataFrame(user_prediction)

user_prediction_df.columns = item_name
user_prediction_df.insert(0,'user_name',user_name)

user_prediction_df = user_prediction_df.style.background_gradient(cmap='Blues')
user_prediction_df.to_html(r'D:\workspace_python\practice\data\pandasTest\user_prediction_df_with_format.html')