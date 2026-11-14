# PHẦN 1 — GIẢI THÍCH CÔNG THỨC COSIN TRONG MFCC

*Trả lời câu hỏi của người hướng dẫn: "công thức cosin kia là gì, dùng để làm gì?" — mạch trình bày đi từ mô hình giọng nói L(f) = H(f) + S(f), qua bộ lọc tam giác Mel, đến giải biến DCT-II và vì sao chỉ giữ 13 hệ số đầu.*

---

## 1. Mô hình giọng nói — tại sao xuất hiện phép CỘNG

### 1.1. Câu chuyện vật lý: hai "cửa hàng" trong cổ họng

Âm giọng (câu nói, tiếng "mở cửa"…) được sinh ra theo đúng mô hình **nguồn – kênh truyền (source–filter)**:

1. **Dây thanh quản (nguồn)** rung động và tạo ra một tín hiệu **điều hòa (harmonic)**: sóng cơ bản có chu kỳ T₀, tần số cơ bản **F₀ (pitch)**, kèm một chuỗi hài F₀, 2F₀, 3F₀… — âm trầm/bổng của mỗi người, và cả trạng thái tâm trạng, đều nằm ở tần số này.
2. **Khoang miệng – lưỡi – môi (kênh truyền)** như một ống cộng hưởng: nó **khuếch đại** một số dải tần và **triệt tiêu** dải khác, tạo ra các đỉnh cộng hưởng gọi là **formant F1, F2, F3** — hình dạng ống phát âm này (gần như độc nhất theo từng người) mới là **"chữ ký" danh tính** của giọng.

### 1.2. Công thức đúng là ở đâu?

Trong dải tần, tiếng giọng = Nguồn × Kênh, nghĩa là **phép NHÂN**:

  L(f) = H(f) · S(f)

- **H(f)** — hàm phổ của kênh truyền (đường bao quanh formant).
- **S(f)** — hàm phổ của nguồn (các gai harmonics xếp cách đều F₀).

Nhân là **khó lọc**: muốn tách H ra khỏi S bằng một lọc thường, ta phải tách hai tín hiệu **trộn lẫn vào nhau** — đó là lý do bước tiếp theo phải đưa phép nhân về phép cộng.

**Trick "cao cấp" nằm ở logarit**: lấy logarit của phổ biên độ, phép **nhân hoá thành cộng** (logarit của tích là tổng của logarit):

  log|L(f)| = log|H(f)| + log|S(f)| = H(f) + S(f)   (ký hiệu rút gọn)

Đây chính là công thức **L(f) = H(f) + S(f)** mà buổi thuyết trình lấy làm mở đầu — một phép cộng trên miền **log-phổ (log-spectrum)**. Trên trục phổ logarit:

| Thành phần | Hình dạng trên log-phổ | Chứa thông tin gì | Giữ hay bỏ cho bài toán danh tính? |
|---|---|---|---|
| log-H(f) — đường bao | **Biến chậm, mượt**, ít "sóng" | Formants **F1, F2, F3** — đặc trưng hình học khoang miệng/lưỡi/môi | **CẦN — giữ lại** (chữ ký danh tính) |
| log-S(f) — chi tiết hài | **Biến nhanh**, gợn sin nhỏ xếp cách đều | Tần số cơ bản **F₀** và chuỗi hài | **KHÔNG cần — bỏ** (thay đổi theo tâm trạng, nội dung câu nói, lại nặng dữ liệu) |

### 1.3. Giây phút ánh sáng bạn cần nói rõ với hội đồng

Câu "lấy phần biến chậm, bỏ phần biến nhanh" nghe quen — vì đó chính là tư tưởng **lọc thông thấp trên miền log-phổ**. Nhưng lọc thông thấp thường có 3 vấn đề (cần chọn hệ số, bị dịch pha, gây trễ). DCT-II cho ta cùng kết quả bằng một **phép nhân ma trận cosin** — tiếp theo ta sẽ thấy nó giải quyết vấn đề này gọn hơn.

---

## 2. Bộ lọc tam giác Mel — nén phổ và giữ lại đúng vùng "chữ ký"

### 2.1. Vì sao không dùng nguyên 257 bin FFT?

FFT 512 điểm trên tín hiệu 16 kHz cho **257 bin dương**, mỗi bin rộng Δf = 31,25 Hz. Phân bố đều theo Hertz là lãng phí tai người: màng nhĩ (cochlea) phân giải tần số theo thang **Mel** — hẹp ở dải thấp, rộng ở dải cao. Vì thế MFCC gom 257 bin vào một số ít **bộ lọc tam giác** đặt trên trục Mel.

### 2.2. Con số 32 và 13 trong dự án — nói rõ để không bị hỏi ngược

| Hệ | Số bộ lọc tam giác Mel | Bước sau lọc | Chú ý |
|---|---|---|---|
| **Pipeline Edge Impulse (cấu hình khối DSP của dự án)** | **32** | **32 log-năng lượng → DCT-II → giữ 13 hệ số | Đây chính là dòng "32 bộ lọc tam giác đi qua DCT-II … lấy 13 hệ số" trong mạch trình bày |
| **Pipeline firmware tự viết (main/voice_auth.cpp)** | 13 | 13 log-năng lượng dùng thẳng, chưa có DCT-II | Là "MFCC rút gọn": vẫn nén theo dải Mel nhưng dừng trước bước cosin |

Nghịch ý cần nói thẳng: **bộ lọc tam giác không lọc trực tiếp F₀ khỏi formant** — nhiệm vụ "tách nhanh/chậm" thuộc về DCT-II ở mục 3. Bộ lọc Mel làm hai việc: (1) nén 257 bin về vài chục giá trị theo thính giác, nhồi đúng trọng số vào vùng formant; (2) **làm mượt phổ**, từ đó phần chi tiết hài chỉ còn là một lớp gợn nhỏ phủ trên đường bao — chuẩn bị cho phép tách ở bước sau.

### 2.3. Lấy log — công thức bắt buộc trước khi cộng được

Sau lọc Mel ta có 32 năng lượng E₁…E₃₂, rồi lấy **logarit**: log(E + ε) với ε nhỏ chống log(0). Có log, phổ giờ nằm trên miền mà phép nhân của hai thành phần đã hoá thành **phép cộng**: vector 32 chiều x = log-H + log-S. Đến đây bài toán tách formants/khỏi harmonics trở thành bài toán tách **thành phần biến chậm khỏi thành phần biến nhanh của một vector có 32 điểm** — chính là việc của DCT-II.

---

## 3. Giải biến cosin DCT-II — chìa khóa trả lời của thầy

### 3.1. Công thức

Sau lọc Mel + log ta có vector x = (x₀, x₁, …, x₃₁) — 32 log-năng lượng sắp theo thứ tự tần số tăng dần. DCT-II biến nó thành 32 hệ số Cₙ:

  Cₙ = Σᵢ₌₀³¹  xᵢ · cos( π · n · (2i + 1) / 64 ),     n = 0, 1, …, 31

(với hệ số chuẩn hóa trực giao: nhân √(1/32) cho n = 0 và √(2/32) cho n ≥ 1 — nhân ma trận trực chuẩn, không đổi tổng năng lượng, không đổi chuẩn Euclid của vector.)

Đọc công thức theo đúng câu hỏi của thầy:
- **Mỗi Cₙ là một phép chiếu giữa phổ log và một hàm cosin có biên độ dao động tăng dần theo bậc n**: n nhỏ → cosin dao động RẤT CHẬM trên 32 điểm; n lớn → cosin dao động RẤT NHANH.
- Vector x sắp theo tần số: dải thấp (băng Mel 1) nằm ở x₀…, dải cao (băng Mel 32) ở x₃₁.

### 3.2. Nhanh/chậm của cosin = tách formants khỏi harmonics

Đây là câu trả lời trung tâm:

- **log-H (đường bao → F1, F2, F3) là phần biến CHẬM** trên trục tần số: có tới 3 đỉnh gồ ghề là cùng, ít sóng nhỏ. Nó chỉ được dựng nên từ những dao động chậm — tức tổng trọng số xᵢ với cosin của **n nhỏ (n = 1, 2, 3,…)**.
- **log-S (harmonics → F₀) là phần biến NHANH**: mỗi hài tạo một gai nhỏ cách đều, 32 băng Mel chạm khoảng vài gai thì hơi lên, vài gai sau lại hơi xuống → dao động dày. Chỉ cosin **n lớn** mới bắt được loại dao động này.
- Như vậy **C₀ đo tổng năng lượng (âm lượng), C₁…C₁₂ miêu tả đường bao (chữ ký danh tính), C₁₃ trở lên miêu tả gợn hài (F₀)**. Giữ đúng 13 hệ số đầu = áp đúng nguyên tắc "giữ F1/F2/F3, bỏ F₀" bằng một phép nhân ma trận duy nhất.

Ví dụ con số nói trước hội đồng: người nói F₀ = 120 Hz → gai hài cách nhau 120 Hz; quanh vùng 1–2 kHz, một chu kỳ gợn chỉ chạm 2–3 băng Mel kề nhau trong 32 băng, tức dao động rất dày → chỉ hệ số bậc cao (từ C₁₃ trở lên, càng gần vùng băng cao bậc càng lên) mới bắt kịp giai điệu dao động đó. Mục 3.3 sẽ bẻ từng bước bằng hình minh họa cho chính phép toán này. F₀ thay đổi (lên giọng, xuống giọng) làm dịch các hệ số cao, nhưng hầu như không lay chuyển C₁–C₁₂ — đó chính là tính ổn định mà bài toán xác thực cần.

### 3.3. Bẻ công thức từng bước: khi 32 thang Mel đi qua DCT-II

Mục này đi chậm từng bước trên một khung thực tế, kèm hình minh họa tái lập trực tiếp công thức DCT-II (số liệu là mô phỏng dựng hình, đúng toán học):

![Hình 1. Ba bước khi 32 log-Mel đi qua DCT-II: (A) vector x = H + S tách sẵn thành đường bao chậm (F1/F2/F3) + gợn nhanh (F₀); (B) cosin bậc 1 khớp đường bao, cosin bậc 15 khớp gợn; (C) năng lượng dồn về C₀–C₁₂, đỉnh gợn F₀ nằm ở C₁₄–C₁₅ và bị loại](_deck_fig/dct_walkthrough.png)

**Bước 1 — 32 giá trị Mel đã "cài sẵn" hai thành phần (hình A).** Sau bộ lọc tam giác và log, mỗi khung là vector x = H + S: đường bao H biến CHẬM, mượt — ba đỉnh là ba formant F1/F2/F3; phủ trên đó là lớp gợn S biến NHANH — chu kỳ hài của nguồn, trên hình minh họa chu kỳ gợn ~ 4,4 băng (tần số gợn này do F₀ và vùng băng quyết định, xem bảng ở Bước 3).

**Bước 2 — mỗi Cₙ là một "điểm tương đồng" giữa x và một hàm cosin (hình B).** Cₙ = Σ xᵢ·cos(π·n·(2i+1)/64) là tích vô hướng: nếu x biến động cùng nhịp với hàm cosin bậc n, từng số hạng trùng dấu và cộng dồn lớn; nếu x chậm trong khi cosin dập dềnh nhanh, từng số hạng liên tục đổi dấu và triệt tiêu gần hết khi cộng. Đối chiếu hai đường trong hình B:

- **cosin n = 1** — trên cả 32 điểm chỉ giảm từ ~ +1 về ~ −1 đúng một lần, tròng dài trên trục tần số ⇒ "vượt qua" nổi đường bao; nhân vào x (năng lượng nằm gọn ở H) cho hệ số lớn.
- **cosin n = 15** — dao động dày gấp nhiều lần, nhịp sin gần trùng chu kỳ gợn S ⇒ đúng "khuôn" của phần biến nhanh; ngoài phần gợn, tất cả số hạng với đường bao H tự triệt tiêu vì H gần hằng trên từng nửa chu kỳ cosin.

**Bước 3 — năng lượng rơi về đâu (hình C).** Biểu đồ 32 hệ số của khung demo nói lên tất cả:

- **C₀** — giá trị trung bình (tổng log-năng lượng của khung = âm lượng), không nép formant cụ thể.
- **C₁–C₃** — các đỉnh đầu tiên của đường bao: chính là **F1, F2, F3** vị trí và cường độ.
- **C₄–C₁₂** — dáng dọc mượt còn lại của đường bao trên vùng băng giữa–cao.
- **C₁₃ trở đi** — gần như 0; riêng **C₁₄, C₁₅ là hai đỉnh nổi bật** (|C₁₄| ≈ 13, |C₁₅| ≈ 10 trong đơn vị hình demo): phần gợn hài F₀ đã dồn trọn về đây — biên độ nhỏ (vài % năng lượng toàn vector) nhưng lớn nhất trong vùng bị loại. Cả cụm C₀–C₁₂ giữ ~ 99,8 % năng lượng vector demo — con số kiểm chứng bằng chính công thức DCT-II.

| Gợn (F₀ × vùng băng quyết định chu kỳ) | Chu kỳ gợn (băng) | Vị trí hệ số đỉnh |
|---|---|---|
| Gợn trong hình minh họa (demo) | ~ 4,4 băng | ~ C₁₄–C₁₅ |
| Gợn nhanh hơn gấp đôi | ~ 2,2 băng | ~ C₂₉ (gần mép 32) |
| Chu kỳ ≤ 1 băng (F₀ cao, vùng băng cao) | gợn dày hơn cả số hệ số 32 | tràn ngoài miền C₀…C₃₁ — mất luôn |

Ghi chú trung thực: vị trí đỉnh chính xác tựa theo F₀ và vùng băng (chu kỳ gợn càng ngắn, đỉnh càng dịch về bậc cao), nhưng nguyên tắc bất di bất dịch: **biến chậm ⇒ dồn về hệ số bậc đầu; biến nhanh ⇒ dồn về hệ số bậc sau**. Đường bao luôn chậm hơn nhiều so với gợn hài, nên ranh giới C₁₂/C₁₃ tách hai thành phần ổn định.

**Bước 4 — "cắt ở 13" là lọc thông thấp trên CHỈ SỐ HỆ SỐ.** Giữ C₀–C₁₂, bỏ C₁₃+ chính là lọc thông thấp trên trục bậc cepstral: không chọn hệ số lọc, không dịch pha, không gây trễ, chỉ tốn một lần nhân ma trận 32×32 và lấy 13 phần tử đầu. Đây là câu chốt để trả thầy: **F1/F2/F3 biến chậm nên khi trao qua cosin hợp với sóng ở các hệ số đầu, năng lượng tập trung hết về đây; F₀ biến nhanh nên dồn vào các hệ số sau (như C₁₄, C₁₅) — và ta bỏ đi.**

### 3.4. Tương quan của hàm cosin — vì sao "khử tương quan" là báu vật

Hai ý nữa khi nói về công thức cosin:

1. **Các hàm cơ sở cos(π·n·(2i+1)/64)** với n khác nhau là **trực giao** trên 32 điểm: tích hai hàm khác nhau bằng đúng 0. Hệ quả: các hệ số Cₙ **gần như không tương quan với nhau** — trong khi các băng log-Mel kề nhau tương quan tới ~0,99 (giọng phát ra phổ mượt). Sau DCT, thông tin được "cào" đều và tách rời vào từng trục riêng — tầng phân loại phía sau (tầng Dense/CNN) học dễ hơn nhiều, và khi cần nén thì cắt bớt hệ số không làm loang thông tin sang các hệ số khác.
2. **Vì sao chọn DCT mà không phải DFT/FFT?** Cùng vào là dữ liệu thực; DCT chỉ sinh phần thực, không sinh phần ảo (tiết kiệm một nửa số học và bộ nhớ); với tín hiệu tương quan cao kiểu đường bao phổ, DCT-II **nén năng lượng tốt hơn cả DFT** — hơn 99% năng lượng nằm trong 1/3 số hệ số đầu. Với MCU, "DFT số phức + nửa phổ dư" là chi phí không cần thiết.

### 3.5. Sơ đồ tổng kết mạch trình bày

  Âm thanh 16 kHz → khung 32 ms (cửa sổ Hann) → FFT 512 → 257 bin
  → 32 bộ lọc tam giác Mel → 32 năng lượng → log → x = log-H + log-S
  → DCT-II (ma trận cosin) → C₀…C₃₁
  → GIỮ 13 hệ số đầu (C₀: âm lượng; C₁–C₁₂: formants F1/F2/F3) → 13 giá trị/khung
  → xếp 31–32 khung → ma trận đặc trưng (31×13 hoặc 32×13) → CNN INT8.

Câu chốt để trả lời thầy: **"Công thức cosin (DCT-II) là bước tách nguồn khỏi kênh ở mức toán học — nó dùng các hàm cosin dao động nhanh chậm khác nhau để phân rã log-phổ: hệ số bậc thấp giữ đường bao (F1/F2/F3, chữ ký danh tính), hệ số bậc cao chứa chu kỳ hài (F₀) và bị loại. Nhờ trực giao, 13 hệ số còn lại gần như không tương quan và nén được tới hơn 99% năng lượng thông tin."**

---

## 4. Ghi chú trung thực: hai pipeline của dự án

Khi hội đồng hỏi sâu, cần phân biệt rõ hai "nhánh MFCC" đang tồn tại song song trong dự án:

| | Pipeline Edge Impulse (khối DSP cấu hình trong Studio) | Pipeline firmware tự viết (main/voice_auth.cpp + train_quantize_export.py) |
|---|---|---|
| Bộ lọc tam giác Mel | **32** | **13** (13 băng × 19 bin) |
| Log | có | có (log(E/512² + 1e-6)) |
| DCT-II | **có → 32 hệ số, giữ 13** | **không** — dùng thẳng 13 log-năng lượng |
| Đầu ra mỗi khung | 13 hệ số MFCC | 13 giá trị log-Mel |
| Mô hình đi kèm | CNN INT8 978 tham số (model EI 5.920 B) | CNN 2D tự huấn luyện ~13.600 tham số (voice_auth.tflite 20.000 B) |

Vì thế, khi nói "32 bộ lọc → DCT-II → 13 hệ số" là đang nói về **pipeline chuẩn MFCC của Edge Impulse** (và của lý thuyết MFCC kinh điển); còn phần firmware tự viết là bản **rút gọn**, đã cắt DCT-II cho nhẹ CPU — cách nén theo dải Mel vẫn giữ phần lớn thông tin đường bao trong 13 kênh, nhưng bước tách gợn hài kém sạch hơn DCT-II. Đây cũng chính là mục "thống nhất hai pipeline" trong các định hướng cải tiến của dự án.

## 5. Bảng trả lời nhanh — dự liệu câu hỏi của thầy

| Câu hỏi có thể gặp | Câu trả lời ngắn |
|---|---|
| "Công thức cosin là gì?" | Giải biến DCT-II: Cₙ = Σ xᵢ·cos(π·n·(2i+1)/64), n = 0…31, nhân ma trận trực giao 32×32 lên 32 log-năng lượng Mel. |
| "Vì sao là cosin mà không phải sin?" | Là phần thực của phép DFT trên chuỗi đối xứng chẵn: chỉ sinh giá trị thực, không phát sinh phần ảo như DFT. |
| "Vì sao nhân đúng mẫu (2i+1)/2N?" | Để các điểm lấy mẫu rơi vào giữa các khoảng nguyên — cơ sở trực giao chuẩn của DCT-II (khác DCT-I lấy mẫu ở cả hai mép), cho ma trận trực chuẩn đơn giản √(1/32) và √(2/32). |
| "Cái nào chứa F₀, cái nào chứa F1/F2/F3?" | Hệ số bậc CAO (C₁₃ trở lên) chứa gợn chu kỳ hài = F₀; hệ số bậc THẤP (C₀ âm lượng, C₁–C₁₂ đường bao) chứa formants F1/F2/F3. |
| "Cái gì cần, cái gì bỏ?" | Cần: C₀–C₁₂ (danh tính nằm ở hình dạng ống phát âm). Bỏ: C₁₃+ (pitch thay đổi theo tâm trạng/nội dung, mang thêm nhiễu, gây overfit dữ liệu nhỏ). |
| "Vì sao giữ đúng 13 chứ không phải 10 hoặc 20?" | Chuẩn của Davis–Mermelstein (1980) và cấu hình Edge Impulse: đủ phủ F1–F3 và độ dốc phổ, còn vượt ~13 là vùng gợn hài/nhiễu; 13 hệ số × 31 khung = 403 đặc trưng vừa tầm mạng nhỏ. |
| "Bỏ 19 hệ số có mất thông tin gì?" | Mất đúng phần biến nhanh của log-phổ (harmonics + chi tiết cao tần). Vì các hệ số tự khử tương quan, phần bị cắt là mất riêng từng hệ số, không loang thông tin sang các phần còn lại; trên dữ liệu tương quan cao, 13 hệ số giữ > 99% năng lượng thông tin. |
