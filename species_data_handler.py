import os
import numpy as np
import joblib
import xgboost 
from sklearn.preprocessing import LabelEncoder
from db_connector import get_db_connection

def get_species_for_location(lat, lon):
    try:
        print("Connecting SQL:", lat, lon)
        sql_path = os.path.join(os.path.dirname(__file__), "DataCollection.sql")
        print("SQL Path:", sql_path)
        model_dir = os.path.join(os.path.dirname(__file__), "XGBModel")
        print("Model directory:", model_dir)
        xgb_model = joblib.load(os.path.join(os.path.dirname(__file__), 'XGBModel', 'xgb_model.joblib'))
        print("XGB Model loaded")
        le = joblib.load(os.path.join(os.path.dirname(__file__), 'XGBModel', 'label_encoder.joblib'))
        print(le)

        with open(sql_path, "r") as f:
            query = f.read()

        conn, tunnel = get_db_connection()
        print("Back to handler")
        
        # try:
        with conn.cursor() as cursor:
            print(lon, lat)
            cursor.execute(query, (lon, lat))
            results = cursor.fetchall()
            print("Results******", results)

            if not results or len(results[0]) == 0:
                return None

            vector = np.array(results[0]).reshape(1, -1)
            
            # Predict the encoded class
            y_pred = xgb_model.predict(vector)
            
            # Convert to original label
            species = le.inverse_transform(y_pred)[0]
            return species
    
    except Exception as e:
        print("Exception occurred:", e)
        import traceback
        traceback.print_exc()
        raise e  
    
    finally:
            conn.close()
            tunnel.close()
