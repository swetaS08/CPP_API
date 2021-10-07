
from flask import Flask, request, render_template, jsonify,json
import pandas as pd
from fetch_intf import dcmetro_desc



app = Flask(__name__, template_folder='templates')



@app.route('/api/interface_details', methods = ['GET','POST'])
def interface_details():

    x = request.get_json()
    device_list = x['devices']
    check_type = x['check_type']
    jdata = json.loads(device_list)
    df = pd.DataFrame(jdata)


    result = globals()[check_type](df)
    print(result)
    result = result.to_json(orient='records')
    print(result)
    return jsonify({'result':result})




if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, host='127.0.0.8', port='5204')
