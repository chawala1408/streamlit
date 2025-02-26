import streamlit as st
import pandas as pd
import pyrebase

# กำหนดค่า config ของ Firebase
config = {
    "apiKey": "AIzaSyAUOr-wqlUhnIVeGgRKOHXkFAqCMHEy_2g",
    "authDomain": "your-project.firebaseapp.com",
    "databaseURL": "https://check-4c4c4-default-rtdb.asia-southeast1.firebasedatabase.app/",
    "storageBucket": ""  # 👈 เพิ่มค่าเป็น string ว่าง
}

# เชื่อมต่อ Firebase
firebase = pyrebase.initialize_app(config)
db = firebase.database()

# ดึงข้อมูลจาก Firebase ทั้ง Pass และ NG
result_pass = db.child('Pass').child('MAC ID').get().val()
result_ng = db.child('NG').child('MAC ID').get().val()

# ฟังก์ชันสำหรับแปลงข้อมูลเป็น DataFrame
def convert_to_dataframe(result, status):
    if result:
        data_list = []
        for key, value in result.items():
            if isinstance(value, dict):
                value['ID'] = key
                value['Status'] = status
                # เพิ่ม Location เป็น 'N/A' สำหรับข้อมูล NG
                if status == 'NG' and 'Localtion' not in value:
                    value['Localtion'] = 'N/A'
                data_list.append(value)
            else:
                data_dict = {'ID': key, 'Value': value, 'Status': status}
                if status == 'NG':
                    data_dict['Localtion'] = 'N/A'
                data_list.append(data_dict)
        return pd.DataFrame(data_list)
    return pd.DataFrame()

# สร้าง DataFrame สำหรับแต่ละประเภท
df_pass = convert_to_dataframe(result_pass, 'Pass')
df_ng = convert_to_dataframe(result_ng, 'NG')

# รวม DataFrame
df = pd.concat([df_pass, df_ng], ignore_index=True)

# ตรวจสอบว่า df มีข้อมูลหรือไม่
if not df.empty:
    # กำหนด columns ที่ต้องการแสดง
    selected_columns = [
        'ID',
        'Board',
        'Localtion',
        'Modbus_RTU',
        'Modbus_TCP',
        'Volt_judge',
        'cpu_judge',
        'RSSI_judge',
        'LED',
    ]

    # เลือกเฉพาะ columns ที่มีอยู่ใน DataFrame
    existing_columns = [col for col in selected_columns if col in df.columns]

    if existing_columns:
        df_selected = df[existing_columns]

        # สร้าง filters
        col1, col2 = st.columns(2)
        
        with col1:
            # Filter สำหรับ Location (เฉพาะข้อมูลที่มี Location)
            st.write("🏢 **เลือกสถานที่:**")
            # กรอง Location ที่ไม่ใช่ 'N/A' สำหรับการแสดงใน dropdown
            valid_locations = sorted([loc for loc in df_selected['Localtion'].unique() if loc != 'N/A'])
            locations = ['ทั้งหมด'] + valid_locations
            selected_location = st.selectbox("", locations)

        with col2:
            # Filter สำหรับ Board
            st.write("🛠️ **เลือกบอร์ด:**")
            boards = ['ทั้งหมด'] + sorted(df_selected['Board'].unique())
            selected_board = st.selectbox("", boards)

        # กรองข้อมูลตาม filters
        df_filtered = df_selected.copy()
        
        if selected_location != 'ทั้งหมด':
            df_filtered = df_filtered[df_filtered['Localtion'] == selected_location]
            
        if selected_board != 'ทั้งหมด':
            df_filtered = df_filtered[df_filtered['Board'] == selected_board]

        st.write("📋 **ข้อมูลจาก Firebase:**")
        st.dataframe(df_filtered, use_container_width=True)

        if not df_filtered.empty:
            with st.expander("✏️ **แก้ไข Location ของ MAC ID**", expanded=False):
                # เลือก MAC ID ที่ต้องการแก้ไข Location
                selected_mac = st.selectbox("🔍 **เลือก MAC ID เพื่อแก้ไข Location:**", df_filtered['ID'].unique())

                if selected_mac:
                    # ดึงค่า Location ปัจจุบันของ MAC ID ที่เลือก
                    current_location = df_filtered[df_filtered['ID'] == selected_mac]['Localtion'].values[0]

                    # ป้อนค่าใหม่สำหรับ Location
                    new_location = st.text_input("✏️ **แก้ไข Location:**", value=current_location)

                    if st.button("💾 **บันทึกการเปลี่ยนแปลง**"):
                        try:
                            # ตรวจสอบว่า MAC ID อยู่ใน Pass หรือ NG
                            mac_path = None
                            if selected_mac in df_pass['ID'].values:
                                mac_path = f"/Pass/MAC ID/{selected_mac}"
                            elif selected_mac in df_ng['ID'].values:
                                mac_path = f"/NG/MAC ID/{selected_mac}"

                            if mac_path:
                                # ✅ ใช้ firebase.put() โดยกำหนด 'Localtion' เป็น key
                                db.child(mac_path).update({"Localtion": new_location})

                                st.success(f"✅ อัปเดต Location เป็น `{new_location}` สำเร็จ!")
                                st.rerun()  # รีเฟรชหน้าเพื่ออัปเดตข้อมูลใหม่
                            else:
                                st.warning("⚠️ ไม่พบ MAC ID ในฐานข้อมูล!")
                        except Exception as e:
                            st.error(f"❌ เกิดข้อผิดพลาด: {e}")


        if selected_location != 'ทั้งหมด' and selected_board != 'ทั้งหมด':
            # รับค่า MAC จาก input
            MAC = st.text_input("🔍 **กรอก MAC ID:**")

            if MAC:
                # กรองข้อมูลใน DataFrame ให้ตรงกับ MAC ที่ป้อน
                df_mac_filtered = df[df['ID'] == MAC]
                
                if not df_mac_filtered.empty:
                    # เลือกเฉพาะคอลัมน์ที่ไม่ได้อยู่ใน selected_columns
                    columns_to_show = [col for col in df_mac_filtered.columns if col not in selected_columns]
                    df_mac_filtered = df_mac_filtered[columns_to_show]
                    
                    # แปลงข้อมูลเป็นรูปแบบ Topic-Value
                    df_topic_value = df_mac_filtered.T.reset_index()
                    df_topic_value.columns = ["Topic", "Value"]
                    
                    st.dataframe(df_topic_value, use_container_width=True)
                else:
                    st.warning(f"⚠️ ไม่พบข้อมูลสำหรับ MAC ID: `{MAC}`")
    else:
        st.error("❌ ไม่มีข้อมูลที่สามารถแสดงได้")
else:
    st.error("❌ ไม่สามารถดึงข้อมูลจาก Firebase ได้ กรุณาตรวจสอบการเชื่อมต่อ")
