import hashlib
import json
import os
import sys
import random
import tkinter as tk
import base64
import uuid
import subprocess
from datetime import datetime
from tkinter import messagebox, ttk
from cryptography.fernet import Fernet
import requests

# Tạo một thư mục tên là "KicodeData" trong AppData của Windows để chứa đề và license
import platform

# Tự động nhận diện hệ điều hành để lưu file data an toàn
if platform.system() == "Windows":
    THU_MUC_DATA = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'KicodeData')
else:
    # Nếu là macOS hoặc Linux, lưu vào thư mục ẩn .kicodedata trong thư mục User
    THU_MUC_DATA = os.path.expanduser('~/.kicodedata')

# Nếu thư mục chưa tồn tại thì tạo mới hoàn toàn
if not os.path.exists(THU_MUC_DATA):
    try:
        os.makedirs(THU_MUC_DATA, exist_ok=True)
    except Exception:
        pass

# Khai báo file License nằm trong thư mục AppData
LICENSE_FILE = os.path.join(THU_MUC_DATA, ".sys_license.dat")

# =========================================================================
# 1. CẤU HÌNH BẢO MẬT ĐỒNG BỘ 
# =========================================================================
cau_khau_quyet_bi_mat = "hongoctrungkienhongoctrungkien99"  # Đủ đúng 32 ký tự

SECRET_FERNET_KEY = base64.urlsafe_b64encode(cau_khau_quyet_bi_mat.encode())
cipher = Fernet(SECRET_FERNET_KEY)


TEN_FILE_CO_BAN = {
    1: "Kiến thức chung về Tin học",
    2: "Mạng LAN và Internet",
    3: "Microsoft Excel",
    4: "Microsoft PowerPoint",
    5: "Microsoft Word"
}

TEN_FILE_NANG_CAO = {
    1: "Microsoft Word Nâng cao",
    2: "Microsoft Excel Nâng cao",
    3: "Microsoft PowerPoint Nâng cao"
}

def lay_duong_dan_resource(relative_path):
    """ Lấy đường dẫn tuyệt đối đến tài nguyên, hoạt động cả khi chạy code thường và khi đã build EXE """
    try:
        # PyInstaller tạo ra một thư mục tạm và lưu đường dẫn trong _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def lay_ma_may_vat_ly():
    try:
        mac_int = uuid.getnode()
        mac_str = ''.join(['{:02X}'.format((mac_int >> i) & 0xff) for i in range(0, 8*6, 8)][::-1])
        
        cmd = 'powershell -ExecutionPolicy Bypass -Command "(Get-CimInstance Win32_ComputerSystemProduct).UUID"'
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        hardware_uuid = subprocess.check_output(cmd, shell=True, startupinfo=startupinfo).decode().strip()
                
        if hardware_uuid and len(hardware_uuid) > 6 and "Error" not in hardware_uuid:
            ma_may_rut_gon = f"PC-{mac_str[:6]}-{hardware_uuid[-6:]}"
        else:
            ma_may_rut_gon = f"PC-{mac_str}"
        return ma_may_rut_gon.upper()
    except Exception:
        try:
            return f"PC-{mac_str[:6]}-BACKUP"
        except Exception:
            return "KRIS-KICODE-22558899"

MA_MAY_HIEN_TAI = lay_ma_may_vat_ly()

# =========================================================================
# 2. THUẬT TOÁN ĐỌC, MÃ HÓA VÀ KIỂM TRA BẢN QUYỀN (CẤU TRÚC KEY MỚI)
# =========================================================================
def generate_key_cu(code, secret):
    if code is None or str(code).strip() == "":
        return ""
    return hashlib.sha256((str(code) + secret).encode()).hexdigest()

def kiem_tra_key_offline_lien_mach(ma_may_hien_tai, key_khach_nhap):
    key = key_khach_nhap.strip()
    # Tổng độ dài: 2 (ngày) + 64 (hash) + 2 (năm) + 2 (tháng) + 2 (gói) = 72 ký tự
    if len(key) != 72:
        return False, "Mã kích hoạt không đúng độ dài hợp lệ!", None, None
    try:
        # Cắt chuỗi theo cấu trúc mới:
        ngay_str = key[0:2]
        hash_part = key[2:66]
        nam_2_so = key[66:68]
        thang_str = key[68:70]
        loai_goi = key[70:72].lower() # Chuyển về viết thường 'cb' hoặc 'nc'

        if loai_goi == "cb":
            secret = "secret_basic"
            ten_goi_chinh_thuc = "CO_BAN"
        elif loai_goi == "nc":
            secret = "secret_advanced"
            ten_goi_chinh_thuc = "NANG_CAO"
        else:
            return False, "Gói phần mềm không hợp lệ!", None, None

        # Kiểm tra tính toàn vẹn của mã máy
        hash_tu_may_khach = generate_key_cu(ma_may_hien_tai, secret)
        if hash_part != hash_tu_may_khach:
            return False, "Mã kích hoạt không dành cho máy tính này!", None, None

        # Khôi phục năm đầy đủ dạng 20xx từ 2 chữ số
        nam_day_du = f"20{nam_2_so}"
        
        # Ghép lại thành chuỗi ngày tháng hoàn chỉnh để kiểm tra hạn dùng
        chuoi_ngay_thang_full = f"{ngay_str}/{thang_str}/{nam_day_du}"
        ngay_het_han = datetime.strptime(chuoi_ngay_thang_full, "%d/%m/%Y")
        ngay_hien_thi = ngay_het_han.strftime("%d/%m/%Y")
        
        if datetime.now() > ngay_het_han:
            return False, f"Bản quyền phần mềm đã hết hạn vào ngày {ngay_hien_thi}!\Vui lòng liên hệ Admin để gia hạn.", None, None

        return True, "Hợp lệ", ten_goi_chinh_thuc, ngay_hien_thi
    except Exception:
        return False, "Mã kích hoạt sai cấu trúc định dạng bản quyền!", None, None

def ghi_file_ban_quyen_an_toan(key_goc):
    try:
        data_ma_hoa = cipher.encrypt(key_goc.encode('utf-8'))
        # Ghi đè file bản quyền vào AppData
        with open(LICENSE_FILE, "wb") as f:
            f.write(data_ma_hoa)
    except Exception as e:
        # In ra màn hình CMD nếu có lỗi xảy ra để dễ kiểm tra khi chạy thử
        print(f"Lỗi không ghi được file License: {e}")

def doc_file_ban_quyen_an_toan():
    if not os.path.exists(LICENSE_FILE):
        return ""
    try:
        with open(LICENSE_FILE, "rb") as f:
            data_ma_hoa = f.read()
        key_goc = cipher.decrypt(data_ma_hoa).decode('utf-8')
        return key_goc.strip()
    except Exception:
        return "FILE_BI_SUA_DOI_TRAI_PHEP"

def giai_ma_va_doc_file_dat(ten_file_goc):
    # Định nghĩa lại đường dẫn đầy đủ trong thư mục AppData
    duong_dan_file = os.path.join(THU_MUC_DATA, ten_file_goc)
    
    if not os.path.exists(duong_dan_file):
        return []
    try:
        with open(duong_dan_file, "rb") as f:
            data_ma_hoa = f.read()
        json_str = cipher.decrypt(data_ma_hoa).decode('utf-8')
        return json.loads(json_str)
    except Exception:
        return []

def chuan_hoa_cau_hoi(raw_list):
    formatted_data = []
    for item in raw_list:
        opts = item.get("options", ["", "", "", ""])
        ans_text = item.get("answer", "")
        dap_an_abc = "A"
        if ans_text in opts:
            idx = opts.index(ans_text)
            dap_an_abc = ["A", "B", "C", "D"][idx]
            
        formatted_data.append({
            "cau_hoi": item.get("question", "Nội dung câu hỏi bị trống"),
            "A": opts[0] if len(opts) > 0 else "",
            "B": opts[1] if len(opts) > 1 else "",
            "C": opts[2] if len(opts) > 2 else "",
            "D": opts[3] if len(opts) > 3 else "", 
            "Dap_An": dap_an_abc
        })
    return formatted_data

# =========================================================================
# 3. GIAO DIỆN CHÍNH VÀ KÍCH HOẠT
# =========================================================================
class AppTracNghiem:
    def __init__(self, root):
        self.root = root
        self.root.title("Phần Mềm Trắc Nghiệm Tin Học - Hồ Ngọc Trung Kiên - 0977797378")
        
        try:
            self.root.state("zoomed")
        except Exception:
            self.root.geometry(f"{self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}+0+0")
            
        self.loai_goi = None
        self.ngay_het_han_hien_thi = ""
        self.kiem_tra_kich_hoat_dau_tien()

    def kiem_tra_kich_hoat_dau_tien(self):
        saved_key = doc_file_ban_quyen_an_toan()
        if saved_key and saved_key != "FILE_BI_SUA_DOI_TRAI_PHEP":
            hop_le, thong_bao, loai_goi, ngay_ht = kiem_tra_key_offline_lien_mach(MA_MAY_HIEN_TAI, saved_key)
            if hop_le:
                self.loai_goi = loai_goi
                self.ngay_het_han_hien_thi = ngay_ht
                self.mo_giao_dien_chinh()
                return
            else:
                messagebox.showwarning("Thông báo bản quyền", thong_bao)
                
        self.mo_giao_dien_nhap_key()

    def mo_giao_dien_nhap_key(self):
        self.frame_key = tk.Frame(self.root, padx=30, pady=30)
        self.frame_key.pack(expand=True)

        logo_path = lay_duong_dan_resource("logo.png")
        if os.path.exists(logo_path):
            try:
                self.img_logo = tk.PhotoImage(file=logo_path)
                if self.img_logo.width() > 150:
                    self.img_logo = self.img_logo.subsample(2, 2)
                lbl_logo_img = tk.Label(self.frame_key, image=self.img_logo)
                lbl_logo_img.pack(pady=(0, 10))
            except Exception:
                pass 

        tk.Label(self.frame_key, text="HỆ THỐNG YÊU CẦU MÃ KÍCH HOẠT SẢN PHẨM", font=("Arial", 16, "bold"), fg="#2C3E50").pack(pady=5)
        
        frame_contact = tk.Frame(self.frame_key, bg="#EBF5FB", padx=15, pady=8, highlightbackground="#AED6F1", highlightthickness=1)
        frame_contact.pack(pady=10, fill="x")
        
        tk.Label(frame_contact, text="📞 Liên hệ đăng ký lấy mã kích hoạt:", font=("Arial", 11, "bold"), bg="#EBF5FB", fg="#1B4F72").pack()
        tk.Label(frame_contact, text="Admin: Hồ Ngọc Trung Kiên  -  Hotline/Zalo: 0977797378", font=("Arial", 12, "bold"), bg="#EBF5FB", fg="#C0392B").pack(pady=2)

        frame_ma_may = tk.LabelFrame(self.frame_key, text=" Mã Máy (Copy gửi cho Admin) ", font=("Arial", 10, "italic"), fg="gray", padx=20, pady=10)
        frame_ma_may.pack(pady=15, fill="x")

        self.lbl_ma_may = tk.Label(frame_ma_may, text=MA_MAY_HIEN_TAI, font=("Courier", 13, "bold"), fg="blue")
        self.lbl_ma_may.pack(side="left", padx=10)

        btn_copy = tk.Button(frame_ma_may, text="📋 Copy Mã Máy", bg="#EBEDEF", font=("Arial", 9, "bold"), padx=10, command=self.sao_chep_ma_may)
        btn_copy.pack(side="right", padx=10)

        tk.Label(self.frame_key, text="Nhập Mã Kích Hoạt Phần Mềm (Key):", font=("Arial", 11, "bold")).pack(pady=(10, 5))
        self.entry_key = tk.Entry(self.frame_key, width=55, font=("Courier", 11, "bold"), fg="purple", justify="center")
        self.entry_key.pack(pady=5)

        btn_kich_hoat = tk.Button(self.frame_key, text="KÍCH HOẠT HỆ THỐNG", bg="#2ECC71", fg="white", font=("Arial", 11, "bold"), padx=25, pady=8, command=self.xu_ly_kich_hoat)
        btn_kich_hoat.pack(pady=20)

    def sao_chep_ma_may(self):
        self.root.clipboard_clear() 
        self.root.clipboard_append(MA_MAY_HIEN_TAI) 
        messagebox.showinfo("Đã sao chép", "Đã copy mã máy vào bộ nhớ tạm thành công!")

    def xu_ly_kich_hoat(self):
        key_nhap = self.entry_key.get().strip()
        hop_le, thong_bao, loai_goi, ngay_ht = kiem_tra_key_offline_lien_mach(MA_MAY_HIEN_TAI, key_nhap)
        if hop_le:
            ghi_file_ban_quyen_an_toan(key_nhap)
            messagebox.showinfo("Thành công", f"Kích hoạt thành công gói: {loai_goi}!\nHạn dùng đến ngày: {ngay_ht}")
            self.loai_goi = loai_goi
            self.ngay_het_han_hien_thi = ngay_ht
            self.frame_key.destroy()
            self.mo_giao_dien_chinh()
        else:
            messagebox.showerror("Lỗi bản quyền", thong_bao)

    def mo_giao_dien_chinh(self):
        ten_goi_viet = "TIN HỌC CƠ BẢN" if self.loai_goi == "CO_BAN" else "TIN HỌC NÂNG CAO"
        
        frame_header = tk.Frame(self.root, padx=20, pady=15)
        frame_header.pack(fill="x")
        
        frame_title_text = tk.Frame(frame_header)
        frame_title_text.pack(side="left", expand=True, padx=(120, 0))
        
        lbl_welcome = tk.Label(frame_title_text, text=f"HỆ THỐNG LUYỆN THI TRẮC NGHIỆM TIN HỌC\n[{ten_goi_viet}]", font=("Arial", 20, "bold"), fg="#1B4F72", justify="center")
        lbl_welcome.pack()
        
        lbl_expiry = tk.Label(frame_title_text, text=f"🗓️ Hạn dùng đến ngày: {self.ngay_het_han_hien_thi}", font=("Arial", 11, "bold"), fg="#27AE60")
        lbl_expiry.pack(pady=(5, 0))
        
        btn_logout = tk.Button(frame_header, text="🚪 Đăng Xuất\n(Đổi Key)", bg="#E74C3C", fg="white", font=("Arial", 10, "bold"), padx=15, pady=5, command=self.xu_ly_dang_xuat)
        btn_logout.pack(side="right", padx=10)

        frame_selection = tk.LabelFrame(self.root, text=" Cấu hình học phần môn ôn luyện chuyên đề ", font=("Arial", 11, "italic"), fg="#7F8C8D", padx=20, pady=15)
        frame_selection.pack(pady=10)
        
        tk.Label(frame_selection, text="Chọn phần dữ liệu:", font=("Arial", 11, "bold")).pack(side="left", padx=10)
        
        self.danh_sach_phan_options = []
        if self.loai_goi == "CO_BAN":
            self.danh_sach_phan_options = [f"Phần {k}: {v}" for k, v in TEN_FILE_CO_BAN.items()]
        else:
            self.danh_sach_phan_options = [f"Phần {k}: {v}" for k, v in TEN_FILE_NANG_CAO.items()]
            
        self.cbo_phan = ttk.Combobox(frame_selection, values=self.danh_sach_phan_options, width=45, font=("Arial", 11), state="readonly")
        self.cbo_phan.pack(side="left", padx=10)
        self.cbo_phan.current(0) 

        btn_sync_github = tk.Button(frame_selection, text="🔄 CẬP NHẬT DỮ LIỆU", bg="#2980B9", fg="white", font=("Arial", 10, "bold"), padx=10, command=self.cap_nhat_du_lieu_tu_github)
        btn_sync_github.pack(side="left", padx=15)

        frame_menu = tk.Frame(self.root)
        frame_menu.pack(pady=40)

        btn_hoc = tk.Button(frame_menu, text="1. CHẾ ĐỘ HỌC\n(Theo từng phần - Hiện sẵn đáp án đúng)", width=32, height=3, bg="#E8F8F5", font=("Arial", 12, "bold"), command=lambda: self.vao_che_do("HOC"))
        btn_hoc.grid(row=0, column=0, padx=15, pady=10)

        btn_on = tk.Button(frame_menu, text="2. CHẾ ĐỘ ÔN TẬP\n(Theo từng phần - Check đáp án trực tiếp)", width=32, height=3, bg="#FEF9E7", font=("Arial", 12, "bold"), command=lambda: self.vao_che_do("ON_TAP"))
        btn_on.grid(row=0, column=1, padx=15, pady=10)

        btn_thi = tk.Button(frame_menu, text="3. CHẾ ĐỘ THI THỬ\n(45 Câu - 30 Phút)", width=32, height=3, bg="#EBF5FB", font=("Arial", 12, "bold"), command=lambda: self.vao_che_do("THI"))
        btn_thi.grid(row=0, column=2, padx=15, pady=10)

    def xu_ly_dang_xuat(self):
        if messagebox.askyesno("Xác nhận", "Bạn có chắc chắn muốn đăng xuất tài khoản để nhập Mã kích hoạt (Key) mới không?"):
            if os.path.exists(LICENSE_FILE):
                os.remove(LICENSE_FILE)
            for widget in self.root.winfo_children():
                widget.destroy()
            self.mo_giao_dien_nhap_key()

    def cap_nhat_du_lieu_tu_github(self):
        if not messagebox.askyesno("Cập nhật hệ thống", "Hệ thống sẽ kết nối Internet để tải dữ liệu mới.\n\nBạn có muốn tiếp tục?"):
            return
            
        danh_sach_tep = [
            "coban_1.dat", "coban_2.dat", "coban_3.dat", "coban_4.dat", "coban_5.dat",
            "nangcao_1.dat", "nangcao_2.dat", "nangcao_3.dat"
        ]
        
        base_url = "https://raw.githubusercontent.com/kienhnt/kicode_data/main/"
        thanh_cong = 0
        loi_files = []
        
        popup_wait = tk.Toplevel(self.root)
        popup_wait.title("Đang tải...")
        popup_wait.geometry("350x100")
        popup_wait.resizable(False, False)
        tk.Label(popup_wait, text="Hệ thống đang đồng bộ dữ liệu ...\nVui lòng chờ trong giây lát!", font=("Arial", 11), pady=20).pack()
        self.root.update()

        for file_name in danh_sach_tep:
            try:
                url_tai = base_url + file_name
                response = requests.get(url_tai, timeout=15)
                
                if response.status_code == 200:
                    # SỬA TẠI ĐÂY: Ghi file vào thư mục AppData an toàn
                    duong_dan_ghi_file = os.path.join(THU_MUC_DATA, file_name)
                    with open(duong_dan_ghi_file, "wb") as f:
                        f.write(response.content)
                    thanh_cong += 1
                else:
                    loi_files.append(file_name)
            except Exception:
                loi_files.append(file_name)
                
        popup_wait.destroy()
        
        if thanh_cong == len(danh_sach_tep):
            messagebox.showinfo("Thành công", f"Đồng bộ hoàn tất! Đã cập nhật thành công dữ liệu.")
        else:
            loi_str = ", ".join(loi_files)
            messagebox.showwarning("Kết quả cập nhật", f"Đã tải thành công {thanh_cong}/{len(danh_sach_tep)} file.\nCác file thất bại hoặc không tìm thấy: {loi_str}")

    def vao_che_do(self, che_do):
        ngan_hang_cau_hoi = []
        
        if che_do == "THI":
            if self.loai_goi == "CO_BAN":
                for i in range(1, 6):
                    raw = giai_ma_va_doc_file_dat(f"coban_{i}.dat")
                    if raw: ngan_hang_cau_hoi.extend(random.sample(raw, min(9, len(raw))))
            else:
                for i in range(1, 4):
                    raw = giai_ma_va_doc_file_dat(f"nangcao_{i}.dat")
                    if raw: ngan_hang_cau_hoi.extend(random.sample(raw, min(15, len(raw))))
        else:
            chi_muc_chon = self.cbo_phan.current() + 1
            ten_tep_goc = f"coban_{chi_muc_chon}.dat" if self.loai_goi == "CO_BAN" else f"nangcao_{chi_muc_chon}.dat"
            raw = giai_ma_va_doc_file_dat(ten_tep_goc)
            ngan_hang_cau_hoi.extend(raw)

        if not ngan_hang_cau_hoi:
            messagebox.showerror("Lỗi dữ liệu", "Không có dữ liệu câu hỏi hoặc file bị thiếu. Vui lòng bấm nút 'CẬP NHẬT DỮ LIỆU' trên thanh cấu hình để tải về máy.")
            return

        formatted_questions = chuan_hoa_cau_hoi(ngan_hang_cau_hoi)
        cua_so_moi = tk.Toplevel(self.root)
        GiaoDienLamBai(cua_so_moi, formatted_questions, che_do)


# =========================================================================
# 4. GIAO DIỆN PHÒNG THI VÀ PHÒNG HỌC
# =========================================================================
class GiaoDienLamBai:
    def __init__(self, window, ds_cau_hoi, che_do):
        self.window = window
        self.window.title(f"Màn hình làm bài - Chế độ: {che_do}")
        
        try:
            self.window.state("zoomed")
        except Exception:
            self.window.geometry(f"{self.window.winfo_screenwidth()}x{self.window.winfo_screenheight()}+0+0")
            
        self.window.grab_set() 
        self.window.focus_force()

        self.ds_cau_hoi = ds_cau_hoi
        self.che_do = che_do
        self.current_index = 0
        self.user_answers = [""] * len(self.ds_cau_hoi)
        self.da_nop_bai = False
        self.thoi_gian_con_lai = 1800  
        
        self.setup_gui()
        if self.che_do == "THI":
            self.chay_dong_ho_dem_nguoc()
        self.hien_thi_cau_hoi_theo_index()

    def setup_gui(self):
        self.frame_top = tk.Frame(self.window, bg="#2C3E50", height=50)
        self.frame_top.pack(fill="x", side="top")

        self.lbl_index = tk.Label(self.frame_top, text="Câu hỏi: 1/45", font=("Arial", 13, "bold"), fg="white", bg="#2C3E50")
        self.lbl_index.pack(side="left", padx=30, pady=10)

        if self.che_do == "THI":
            self.lbl_timer = tk.Label(self.frame_top, text="Thời gian còn lại: 30:00", font=("Arial", 13, "bold"), fg="#F1C40F", bg="#2C3E50")
            self.lbl_timer.pack(side="right", padx=30, pady=10)

        self.lbl_cau_hoi = tk.Label(self.window, text="Nội dung câu hỏi...", font=("Arial", 14, "bold"), wraplength=1200, justify="left", anchor="w")
        self.lbl_cau_hoi.pack(pady=35, padx=50, fill="x")

        self.frame_dap_an = tk.Frame(self.window)
        self.frame_dap_an.pack(pady=10, padx=50, fill="x")

        self.btn_A = tk.Button(self.frame_dap_an, text="A.", font=("Arial", 12), anchor="w", padx=20, bg="white", relief="groove", bd=2, command=lambda: self.click_chon_dap_an("A"))
        self.btn_A.pack(fill="x", pady=6)

        self.btn_B = tk.Button(self.frame_dap_an, text="B.", font=("Arial", 12), anchor="w", padx=20, bg="white", relief="groove", bd=2, command=lambda: self.click_chon_dap_an("B"))
        self.btn_B.pack(fill="x", pady=6)

        self.btn_C = tk.Button(self.frame_dap_an, text="C.", font=("Arial", 12), anchor="w", padx=20, bg="white", relief="groove", bd=2, command=lambda: self.click_chon_dap_an("C"))
        self.btn_C.pack(fill="x", pady=6)

        self.btn_D = tk.Button(self.frame_dap_an, text="D.", font=("Arial", 12), anchor="w", padx=20, bg="white", relief="groove", bd=2, command=lambda: self.click_chon_dap_an("D"))
        self.btn_D.pack(fill="x", pady=6)

        self.lbl_goi_y = tk.Label(self.window, text="", font=("Arial", 13, "bold"))
        self.lbl_goi_y.pack(pady=15)

        frame_nav = tk.Frame(self.window)
        frame_nav.pack(side="bottom", pady=15)

        tk.Button(frame_nav, text="◀ Câu Trước", width=16, height=2, command=self.quay_lai_cau_truoc, font=("Arial", 11, "bold"), bg="#EAEDED").grid(row=0, column=0, padx=15)
        
        if self.che_do in ["ON_TAP"]:
            text_nut = "📊 Tiến Độ Ôn Tập" if self.che_do == "ON_TAP" else "📊 Thống Kê Bài Làm"
            self.btn_check_tiendo = tk.Button(frame_nav, text=text_nut, width=22, height=2, command=self.kiem_tra_so_cau_dung, font=("Arial", 11, "bold"), bg="#D4E6F1", fg="#1B4F72")
            self.btn_check_tiendo.grid(row=0, column=1, padx=15)

        tk.Button(frame_nav, text="Câu Tiếp Theo ▶", width=16, height=2, command=self.qua_cau_tiep_theo, font=("Arial", 11, "bold"), bg="#EAEDED").grid(row=0, column=2, padx=15)

        if self.che_do == "THI":
            self.btn_nop_bai = tk.Button(frame_nav, text="NỘP BÀI THI CHẤM ĐIỂM", bg="#E74C3C", fg="white", font=("Arial", 11, "bold"), width=25, height=2, command=self.xu_ly_nop_bai)
            self.btn_nop_bai.grid(row=0, column=3, padx=50)

        master_grid_frame = tk.LabelFrame(self.window, text=" Danh Sách Bảng Câu Hỏi Làm Bài ", font=("Arial", 10, "bold"), fg="#566573", padx=15, pady=10)
        master_grid_frame.pack(side="bottom", fill="x", padx=50, pady=15)

        canvas_container = tk.Canvas(master_grid_frame, height=200, borderwidth=0, highlightthickness=0)
        self.frame_o_chu_so = tk.Frame(canvas_container)
        
        scrollbar_o = tk.Scrollbar(master_grid_frame, orient="vertical", command=canvas_container.yview, width=10)
        canvas_container.configure(yscrollcommand=scrollbar_o.set)
        
        scrollbar_o.pack(side="right", fill="y")
        canvas_container.pack(side="bottom", fill="x", expand=True)
        canvas_container.create_window((0,0), window=self.frame_o_chu_so, anchor="nw")
        
        self.buttons_o_so = []
        so_o_tren_hang = 24 

        for i in range(len(self.ds_cau_hoi)):
            btn_so = tk.Button(self.frame_o_chu_so, text=f"{i + 1:02d}", width=4, font=("Arial", 10, "bold"), 
                               bg="white", fg="#2C3E50", relief="solid", bd=1, activebackground="#D4E6F1",
                               command=lambda idx=i: self.chuyen_nhanh_den_cau(idx))
            btn_so.grid(row=i // so_o_tren_hang, column=i % so_o_tren_hang, padx=4, pady=4)
            self.buttons_o_so.append(btn_so)
            
        self.frame_o_chu_so.update_idletasks()
        canvas_container.config(scrollregion=canvas_container.bbox("all"))

    def hien_thi_cau_hoi_theo_index(self):
        self.btn_A.config(bg="white", fg="black", state="normal")
        self.btn_B.config(bg="white", fg="black", state="normal")
        self.btn_C.config(bg="white", fg="black", state="normal")
        self.btn_D.config(bg="white", fg="black", state="normal")
        self.lbl_goi_y.config(text="")

        cau_hien_tai = self.ds_cau_hoi[self.current_index]

        self.lbl_index.config(text=f"Câu hỏi: {self.current_index + 1}/{len(self.ds_cau_hoi)}")
        self.lbl_cau_hoi.config(text=cau_hien_tai["cau_hoi"])
        self.btn_A.config(text="A. " + cau_hien_tai["A"])
        self.btn_B.config(text="B. " + cau_hien_tai["B"])
        self.btn_C.config(text="C. " + cau_hien_tai["C"])
        self.btn_D.config(text="D. " + cau_hien_tai["D"])

        for i, btn in enumerate(self.buttons_o_so):
            da_chon_cau_nay = self.user_answers[i]
            dung_cau_nay = self.ds_cau_hoi[i]["Dap_An"]
            
            # ƯU TIÊN 1: Nếu ĐÃ NỘP BÀI THI, giữ nguyên màu kết quả cho toàn bộ bảng ô số
            if self.da_nop_bai:
                if da_chon_cau_nay == "":
                    btn.config(bg="#F9E79F", fg="black", bd=1)  # Màu Vàng - Chưa chọn
                elif da_chon_cau_nay == dung_cau_nay:
                    btn.config(bg="#A5D6A7", fg="black", bd=1)  # Màu Xanh lá - Đúng
                else:
                    btn.config(bg="#EF9A9A", fg="black", bd=1)  # Màu Đỏ - Sai
                    
                # Riêng câu đang mở xem lại sau khi nộp bài thì làm viền đậm hơn một chút để phân biệt
                if i == self.current_index:
                    btn.config(bd=2, relief="solid")
                    
            # ƯU TIÊN 2: Nếu CHƯA NỘP BÀI, hiển thị theo trạng thái đang làm bài bình thường
            else:
                if i == self.current_index:
                    btn.config(bg="#E5E7E9", fg="black", bd=2)  # Ô đang mở xem hiện tại màu xám nhạt
                elif da_chon_cau_nay != "":
                    if self.che_do == "ON_TAP":
                        if da_chon_cau_nay == dung_cau_nay:
                            btn.config(bg="#A5D6A7", fg="black", bd=1)
                        else:
                            btn.config(bg="#EF9A9A", fg="black", bd=1)
                    else:
                        # Chế độ thi thử chưa nộp bài thì hiện màu xanh dương thông thường
                        btn.config(bg="#3498DB", fg="white", bd=1)
                else:
                    btn.config(bg="white", fg="#2C3E50", bd=1)

        if self.che_do == "HOC":
            dung = cau_hien_tai["Dap_An"]
            getattr(self, f"btn_{dung}").config(bg="#A5D6A7")
            self.lbl_goi_y.config(text=f"ĐÁP ÁN ĐÚNG: {dung}", fg="#27AE60")

        da_chon = self.user_answers[self.current_index]
        dung = cau_hien_tai["Dap_An"]

        if da_chon and not self.da_nop_bai:
            if self.che_do == "ON_TAP":
                if da_chon == dung:
                    getattr(self, f"btn_{da_chon}").config(bg="#A5D6A7")
                    self.lbl_goi_y.config(text="ĐÚNG RỒI!", fg="#27AE60")
                else:
                    getattr(self, f"btn_{da_chon}").config(bg="#EF9A9A")
                    getattr(self, f"btn_{dung}").config(bg="#A5D6A7")
                    self.lbl_goi_y.config(text=f"SAI RỒI! Đáp án đúng là: {dung}", fg="#C0392B")
            elif self.che_do == "THI":
                getattr(self, f"btn_{da_chon}").config(bg="#D4E6F1")

        if self.da_nop_bai:
            self.btn_A.config(state="disabled")
            self.btn_B.config(state="disabled")
            self.btn_C.config(state="disabled")
            self.btn_D.config(state="disabled")

            getattr(self, f"btn_{dung}").config(bg="#A5D6A7")
            if da_chon != "" and da_chon != dung:
                getattr(self, f"btn_{da_chon}").config(bg="#EF9A9A")

            if da_chon == "":
                self.lbl_goi_y.config(text=f"Bạn bỏ trống câu này! Đáp án đúng là: {dung}", fg="#D35400")
            elif da_chon == dung:
                self.lbl_goi_y.config(text=f"Chúc mừng! Bạn trả lời chính xác. Đáp án: {dung}", fg="#27AE60")
            else:
                self.lbl_goi_y.config(text=f"Sai rồi! Bạn chọn {da_chon}. Đáp án đúng là: {dung}", fg="#C0392B")

    def click_chon_dap_an(self, lua_chon):
        if self.da_nop_bai: return
        if self.che_do == "ON_TAP" and self.user_answers[self.current_index] != "":
            return

        self.user_answers[self.current_index] = lua_chon
        self.hien_thi_cau_hoi_theo_index()

    def kiem_tra_so_cau_dung(self):
        tong_so_cau = len(self.ds_cau_hoi)
        so_cau_da_lam = sum(1 for ans in self.user_answers if ans != "")
        
        if so_cau_da_lam == 0:
            messagebox.showinfo("Tiến độ bài làm", "Bạn chưa chọn đáp án cho bất kỳ câu hỏi nào!", parent=self.window)
            return

        so_cau_dung = 0
        for i, da_chon in enumerate(self.user_answers):
            if da_chon != "" and da_chon == self.ds_cau_hoi[i]["Dap_An"]:
                so_cau_dung += 1
                
        so_cau_sai = so_cau_da_lam - so_cau_dung
        ty_le_chinh_xac = round((so_cau_dung / so_cau_da_lam) * 100, 1)
        
        chuoi_thong_ke = (
            f"📊 THỐNG KÊ TIẾN ĐỘ BÀI LÀM:\n"
            f"----------------------------------------\n"
            f"▪️ Tổng số câu của đề: {tong_so_cau} câu.\n"
            f"▪️ Số câu bạn ĐÃ LÀM: {so_cau_da_lam} câu.\n"
            f"▪️ Số câu trả lời ĐÚNG: {so_cau_dung} câu.\n"
            f"▪️ Số câu trả lời SAI: {so_cau_sai} câu.\n"
            f"----------------------------------------\n"
            f"🎯 Tỷ lệ chính xác (trên số câu đã làm): {ty_le_chinh_xac}%"
        )
        messagebox.showinfo("Thống kê tiến độ", chuoi_thong_ke, parent=self.window)

    def chay_dong_ho_dem_nguoc(self):
        if self.thoi_gian_con_lai > 0 and not self.da_nop_bai:
            self.thoi_gian_con_lai -= 1
            phut = self.thoi_gian_con_lai // 60
            giay = self.thoi_gian_con_lai % 60
            self.lbl_timer.config(text=f"Thời gian còn lại: {phut:02d}:{giay:02d}")
            self.window.after(1000, self.chay_dong_ho_dem_nguoc)
        elif self.thoi_gian_con_lai == 0 and not self.da_nop_bai:
            self.xu_ly_nop_bai()

    def xu_ly_nop_bai(self):
        if self.da_nop_bai: return
        
        if self.thoi_gian_con_lai > 0:
            tong_so_cau = len(self.ds_cau_hoi)
            so_cau_da_lam = sum(1 for ans in self.user_answers if ans != "")
            
            chuoi_canh_bao = f"Bạn mới làm được {so_cau_da_lam}/{tong_so_cau} câu hỏi.\n\nBạn có chắc chắn muốn nộp bài thi sớm không?"
            if so_cau_da_lam == tong_so_cau:
                chuoi_canh_bao = f"Bạn đã hoàn thành đủ {so_cau_da_lam}/{tong_so_cau} câu hỏi.\n\nBạn có chắc chắn muốn nộp bài để kết thúc không?"
                
            if not messagebox.askyesno("Xác nhận nộp bài sớm", chuoi_canh_bao, parent=self.window):
                return

        self.da_nop_bai = True
        so_cau_dung = 0

        for i, cau in enumerate(self.ds_cau_hoi):
            da_chon = self.user_answers[i]
            dung = cau["Dap_An"]

            if da_chon == "":
                self.buttons_o_so[i].config(bg="#F9E79F", fg="black")  
            elif da_chon == dung:
                so_cau_dung += 1
                self.buttons_o_so[i].config(bg="#A5D6A7", fg="black")  
            else:
                self.buttons_o_so[i].config(bg="#EF9A9A", fg="black")  

        diem_so = round((so_cau_dung / len(self.ds_cau_hoi)) * 10, 2)
        messagebox.showinfo("KẾT QUẢ THI THỬ", f"Bài thi kết thúc!\nSố câu đúng: {so_cau_dung}/{len(self.ds_cau_hoi)}\nĐiểm số đạt được: {diem_so} / 10 Điểm!", parent=self.window)

        self.window.focus_force()
        self.current_index = 0
        self.hien_thi_cau_hoi_theo_index()

    def quay_lai_cau_truoc(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.hien_thi_cau_hoi_theo_index()

    def qua_cau_tiep_theo(self):
        if self.current_index < len(self.ds_cau_hoi) - 1:
            self.current_index += 1
            self.hien_thi_cau_hoi_theo_index()

    def chuyen_nhanh_den_cau(self, index):
        self.current_index = index
        self.hien_thi_cau_hoi_theo_index()


if __name__ == "__main__":
    giao_dien_goc = tk.Tk()
    chay_app = AppTracNghiem(giao_dien_goc)
    giao_dien_goc.mainloop()