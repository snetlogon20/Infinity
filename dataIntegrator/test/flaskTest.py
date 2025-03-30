from flask import Flask, request, jsonify, send_file
import json
import requests

app = Flask(__name__, static_folder='static')

# methods: 指定请求方式
@app.route('/process', methods=['POST'])
def process_data():
    # 请求方式为post时，可以使用 request.get_json()接收到JSON数据
    data = request.get_json()  # 获取 POST 请求中的 JSON 数据
    print(data)
    # 处理数据
    # 调用do_something_with_data函数来处理接收到的数据。
    #processed_data = do_something_with_data(data)

    # 请求方得到处理后的数据
    #return jsonify(processed_data)

@app.route('/getData', methods=['get'])
def get_data():
    # 请求方式为post时，可以使用 request.get_json()接收到JSON数据
    data = request.get_json()  # 获取 POST 请求中的 JSON 数据
    request.args.get("a")

    dict1 = {}
    dict2 = {}
    dict3 = {}
    dict3['a'] = 'a1'
    dict2['b'] = dict3
    dict1['c'] = dict2
    json_string = json.dumps(dict1)

    #print("dd：" + data)
    # 处理数据
    # 调用do_something_with_data函数来处理接收到的数据。
    #processed_data = do_something_with_data(data)
    processed_data="dddd"
    print(json_string)

    # 请求方得到处理后的数据
    return jsonify(json_string)

@app.route('/getData1', methods=['get'])
def get_data1():
    response = requests.get(
        'http://127.0.0.1:5000/getData',
        params=request.args,
        data=request.data
    )
    print(response)
    return("a")


@app.route('/getFile', methods=['get'])
def get_file():
    # 请求方式为post时，可以使用 request.get_json()接收到JSON数据
    data = request.get_json()  # 获取 POST 请求中的 JSON 数据
    #print("dd：" + data)

    # import base64
    # img_stream = ''
    # with open("D:\\workspace_python\\practice\\data\\citi.png", 'rb') as img_f:
    #     img_stream = img_f.read()
    #     img_stream = base64.b64encode(img_stream).decode()
    # img_stream
    #
    # return img_stream

    return send_file('D:\\workspace_python\\practice\\data\\citi.png', mimetype='image/jpg')

if __name__ == '__main__':
    app.run()