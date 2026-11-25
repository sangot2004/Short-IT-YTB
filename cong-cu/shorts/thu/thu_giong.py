import time
from vieneu import Vieneu
tts = Vieneu()
txt = "Tuần này, Microsoft ba trăm sáu mươi lăm gặp sự cố kéo dài nhiều giờ. Hàng triệu người dùng không thể mở email và tài liệu. Đây là bài học lớn cho các kỹ sư dữ liệu về việc thiết kế hệ thống dự phòng."
for v in ["Mai Anh","Minh Đức","Hải Đăng"]:
    t=time.time(); a=tts.infer(txt, voice=v); tts.save(a, f"thu/{v.replace(' ','_')}.wav"); print(v, round(time.time()-t,1),"s")
