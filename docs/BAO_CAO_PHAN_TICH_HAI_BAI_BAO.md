# BÁO CÁO PHÂN TÍCH VÀ SO SÁNH HAI BÀI BÁO KHOA HỌC

### Liên quan đến lớp giọng nói của dự án Edge AI — Khóa cửa thông minh xác thực hai lớp (giọng nói + khuôn mặt) trên ESP32-S3

---

## 1. MỤC ĐÍCH VÀ PHẠM VI CỦA BÁO CÁO

Báo cáo này được lập phục vụ cho bài toán **tổng quan tài liệu (literature review)** của đồ án *Khóa cửa thông minh hai lớp xác thực (giọng nói + khuôn mặt) trên Edge AI*. Trọng tâm là **lớp xác thực giọng nói** của dự án — vì hai bài báo được chọn đều liên quan trực tiếp đến: đặc trưng MFCC, keyword spotting (KWS)/phân loại âm học, lượng hóa INT8 hậu-huấn luyện (PTQ), triển khai suy luận TensorFlow Lite Micro (TFLM/LiteRT for Microcontrollers) trên vi điều khiển hạn chế tài nguyên.

Hai bài báo được phân tích, **cả hai đều công bố chuẩn năm 2026**:

| # | Bài báo | Tên viết tắt |
|---|---|---|
| 1 | Medur P., Lubbers M., Mauša G. — "Resource-Constrained Keyword Spotting With Quantized CNNs: Implementation Strategies and Performance Trade-Offs", International Journal of Intelligent Systems (Wiley), Vol. 2026, Issue 1, Article 2317323, DOI: 10.1155/int/2317323 | Medur-2026 |
| 2 | Wang Z., Yu G. — "A Sensor-Based TinyML Acoustic Monitoring System for Edge-Side Animal Sound Recognition on Resource-Constrained Microcontrollers", Sensors 2026, 26(13), 3972, DOI: 10.3390/s26133972 | Sensors-2026 |

Điểm đặc biệt của cặp bài này: **bài 1 (Medur-2026) triển khai trên chính dòng ESP32-S3 mà dự án đang dùng** (ESP32-S3-EYE, nhân kép Xtensa LX7) — tức bài toán, nền tảng và pipeline gần như trùng hoàn toàn với lớp giọng nói của dự án; bài 2 (Sensors-2026) là **chuẩn mực phương pháp luận** về đồng bộ đặc trưng giữa máy tính huấn luyện (PC) và vi điều khiển (MCU) cùng đo lường hệ thống. Một bài cho "trực kế phần cứng", một bài cho "chuẩn mực đo lường" — hai góc bổ sung nhau trọn vẹn cho đối chiếu dự án.

Mục tiêu của báo cáo gồm bốn phần:
1. Trình bày tóm lược có hệ thống phương pháp và kết quả của hai bài báo.
2. Đánh giá phê phán điểm mạnh và điểm yếu phương pháp luận của từng bài.
3. So sánh trực tiếp hai bài báo với nhau và so sánh chi tiết với lớp giọng nói của dự án.
4. Rút ra bài học và khuyến nghị cụ thể để hoàn thiện dự án.

Một ghi chú trung thực cần nêu ngay từ đầu: lớp giọng nói của dự án **đã có kết quả validation nội bộ (accuracy 83,33%, F1-weighted 0,84, suy hao 0 điểm phần trăm khi FP32 → INT8) nhưng chưa được đo trên bộ kiểm thử độc lập chính thức**, nên toàn bộ phép so sánh với dự án trong báo cáo này là **so sánh về kiến trúc, phương pháp và cấu hình kỹ thuật**, không phải so sánh trên cùng một bộ số đo chuẩn tạp chí. Khoảng trống này chính là một trong những khuyến nghị quan trọng nhất rút ra từ việc đọc hai bài báo (mục 6).

---

## 2. TÓM LƯỢC NỘI DUNG HAI BÀI BÁO

### 2.1. Medur-2026 — Keyword spotting với CNN lượng tử hóa trên vi điều khiển hạn chế tài nguyên

#### 2.1.1. Bối cảnh và mục tiêu

Các hệ thống nhận giọng trên thiết bị biên thường chạy kiến trúc **hai pha**: pha 1 luôn-bật dùng bộ KWS nhẹ để dò từ khóa "wake word"; khi phát hiện từ khóa mới kích hoạt pha 2 — một mô hình nhận thức nói nặng (cục bộ hoặc đám mây). Bài toán cốt lõi của pha 1 là: giữ độ chính xác chấp nhận được trong giới hạn bộ nhớ, điện năng và thời gian thực của vi điều khiển.

Bài viết này là bước **đưa lý thuyết ra thiết bị thật** của chính nhóm tác giả: nghiên cứu nền tảng trước của cùng nhóm (Medur et al., MIPRO 2025) đã khảo sát 10 kiến trúc CNN cho KWS trên máy tính; bài 2026 này chọn kiến trúc tốt nhất theo chuẩn thương lượng (Model 7), retrain theo chuẩn đánh giá 12 lớp của thư viện Speech Commands (10 từ khóa mục tiêu + "silence" + "unknown"), rồi triển khai INT8 trên nền **ESP32-S3-EYE**.

Hai đóng góp kỹ thuật tuyên bố:

1. **So sánh có kiểm soát trên thiết bị với BC-ResNet** (kiến trúc KWS gọn thuộc top hiện đại) — chứng minh: **gọn mô hình không đồng nghĩa triển khai hiệu quả**; thời gian suy luận đo được trên thiết bị và độ bền lượng tử mới là tiêu chuẩn quyết định.
2. **Kiểm chứng ngoài điều kiện phòng thí nghiệm**: đánh giá bằng người nói tiếng Anh **phi bản ngữ** và giọng **tổng hợp TTS** để định lượng khoảng cách giữa accuracy benchmark và accuracy thực địa.

#### 2.1.2. Nền tảng phần cứng

**ESP32-S3-EYE**: nhân kép Xtensa LX7 @ 240 MHz, 512 KB SRAM, **8 MB PSRAM**, 8 MB Quad-SPI flash, micro I2S tích hợp trên bo — **cùng dòng chip với dự án của chúng ta** (dự án dùng ESP32-S3 + INMP441 qua I2S + PSRAM 8 MB). Đây là lý do bài này trở thành **đối chiếu trực kế phần cứng** nhiều tránh né nhất.

Phần mềm: LiteRT for Microcontrollers (TFLM) và ESP-IDF V5.0; mô hình INT8 được chuyển sang **mảng C** nhúng trực tiếp trong firmware, chiếm **0,67 MB**; tensor arena lớn **1.000 kB** được cấp phát trong PSRAM. Chiến lược bộ nhớ phân tầng: buffer nặng (FFT, hệ số bộ lọc Mel, MFCC) đặt ngoài PSRAM; cấu trúc thời gian-cuất (timing-critical) giữ trong SRAM nội.

#### 2.1.3. Dữ liệu và chuẩn đánh giá

- Dữ liệu: **Google Speech Commands Dataset V0.02** — 105.829 bản ghi, mỗi bản 1 giây, 35 từ, 2.618 người nói.
- Chuẩn 12 lớp của Warden: 10 từ mục tiêu ("yes", "no", "up", "down", "left", "right", "on", "off", "stop", "go") + 2 lớp phụ ("silence", "unknown"; mỗi lớp ~10% dữ liệu).
- Huấn luyện và đánh giá với **10-fold cross-validation, phân chia 80/10/10 (train/validation/test)**; ghi chú quan trọng: **ràng buộc độc lập người nói (speaker-independent)** — mọi bản ghi của một người chỉ nằm trong một split.

#### 2.1.4. Đặc trưng MFCC và cấu hình rút gọn cho chạy thời gian thực

Cấu hình huấn luyện: tín hiệu hạ mẫu 16 kHz → **8 kHz**; cửa sổ **25 ms**, bước **20 ms**, **13 hệ số MFCC/khung**, ma trận đặc trưng **13×50** — khác chuẩn BC-ResNet (40 spectral log-Mel @ 16 kHz): tensor vào nhỏ hơn đáng kể, tầng chập tối ưu nhỏ hơn, arena nổ nhỏ hơn, MAC/lần suy luận ít hơn — thiết kế **theo "khoang bộ nhớ", không theo accuracy tuyệt đối**.

Dòng pipeline MFCC **chạy chính on-device** (được viết bằng toán tử C++ đơn giản hóa để tái hiện pipeline trên PC):

| Bước | Đặc tả |
|---|---|
| Resampling | 16 kHz → 8 kHz bằng **FIR 5 tap** đối xứng [0,0625; 0,25; 0,375; 0,25; 0,0625] (thay cho FFT-based resampling SciPy phức tạp trên PC) |
| Framing | khung 25 ms / hop 20 ms → **50 khung** từ 1 giây |
| Windowing | Hann, N = 200 |
| FFT | **256 điểm**; chỉ dùng 128 bin nửa phổ |
| Mel | **20 bộ lọc tam giác**, dải 300–4000 Hz; chuẩn hóa theo bề rộng băng (energy đo nhất quán) |
| Log | logarit tự nhiên, ε = 10⁻¹⁰ |
| DCT | **DCT-II ra 13 hệ số**; **hệ số C₀ được thay bằng log-Energy của khung** (thông tin âm lượng) |
| Chuẩn hóa ôs | transpose ra ma trận 13×50, mã INT8, thang **scale = 0,359** và **zero_point = 42** |
| Suy luận | TFLM; INT8 arithmetic thuần |

Đây là điểm **giống nhất giữa bài báo và dự án** ở khâu đặc trưng: cả hai đều nhấn mạnh "MFCC phải retraining-viết-khớp trên chip" và hệ số năng lượng C₀ có tính phân loại quan trọng. Khác biệt lớn nhất: bài của Sensors-2026 **kiểm chứng định lượng độ khớp đặc trưng (cosine ≈ 1)**, trong khi bài này **không công bố kiểm chứng cosine giữa pipeline PC và pipeline chip** — chỉ mô tả toán tử tương đương cấu trúc.

#### 2.1.5. Kiến trúc mô hình và so sánh có kiểm soát với BC-ResNet

Mô hình triển khai là **CNN 2D gọn** đầu vào 13×50 một kênh:

- 3 khối [Conv2D 3×3, lần lượt **32/64/128 filter** → ReLU → MaxPool]
- Flatten → **Dense 128** ReLU + **Dropout 0,5** → Softmax 12 lớp.
- Tổng tham số: **684.172**.

Quy trình chọn kiến trúc (đáng học):

| Cấu hình | FP32 (acc / size) | INT8 (acc / size) | Latency on-device |
|---|---|---|---|
| Model 4 (nhỏ nhất >80%) | ~0,16 MB | — | chưa được chọn |
| **Model 7 (đã chọn)** | 90,04% / 7,9 MB; F1 0,9033 | **89,58%** / 0,68 MB; F1 0,9037 | **145,19 ± 0,01 ms** |
| BC-ResNet (chạy lại trên cùng MFCC 13×50) | 89,75% / 1,1 MB; F1 0,8997 | 85,35% / 142,9 kB; F1 0,8569 | 365,22 ± 0,04 ms |

Phát hiện chính (PW này): BC-ResNet INT8 **tệ hơn 4,4 điểm phần trăm** sau lượng tử (85,35% vs 89,75% FP32) trong khi Model 7 **giữ nguyên < 0,5 điểm**; BC-ResNet nhẹ hơn (142,9 kB) nhưng **suy luận chậm hơn 2,5 lần** do toán tử chưa được tối ưu kernel cho chip nhúng. Kết luận nguyên tắc: **size mô hình không phải tiêu chuẩn duy nhất** — phải đo độ bền lượng tử và thời gian suy luận trên thiết bị thật.

#### 2.1.6. Hệ thống thời gian thực

- **FreeRTOS nhân kép**: 1 nhân thu âm liên tục; nhân 2 trích đặc trưng + suy luận — giải nghẽn cổ chai (bottleneck) của kiến trúc đơn nhân.
- **VAD có sàn nhiễu thích nghi**: chỉ kích hoạt khi năng lượng giọng > **2×** mức nền; đo **preroll buffer 200 ms** đảm bảo gồm cả đầu từ khóa; dừng khi phát hiện 400 ms im lặng hoặc đủ 1 giây — tối giản phải cứ kiện suy luận trên đoạn im.

#### 2.1.7. Kết quả

| Chỉ số | Giá trị |
|---|---|
| Accuracy INT8 (phòng lab, Speech Commands) | **89,58%** (F1 0,9037), model 0,68 MB |
| Suy hao INT8 so FP32 | < 0,5 điểm (90,04% → 89,58%) |
| Accuracy suy luận on-device | 145,19 ± 0,01 ms |
| Thí nghiệm người thật (13 phi bản ngữ, 8 nam/5 nữ, 18–33 tuổi, mỗi từ x10, 1.430 lượt) | **81,82%** (F1 0,8229) — suy giảm ~8,2 điểm so lab |
| Khoảng cách theo từng người nói | 74,55% → 94,55% |
| Coupling độ tự tin điểm số | trung bình 87,62% (đúng: 91,52% / nhầm: 70,05%) |
| Lỗi phổ biến nhất | "no" → "go" 48 lần (18,4% số lỗi); "off" → "on" 18 lần |
| Ngưỡng tin cậy ≥ 0,7 | 81,82% → **80,01%** (−1,81 điểm; 122 dự đoán đúng nhưng tin cậy < 0,7 ≈ 8,5%) |
| Thí nghiệm giọng tổng hợp (10 giọng AI Mỹ) | **90,06%** (F1 0,9071); giọng AI: 62,73% → 100%; ngưỡng 0,7 chỉ còn −0,04 điểm |

Ba phát hiện quan trọng:

1. **Khoảng cách lab–thực địa có năng lượng định lượng**: 89,58% (lab) → 81,82% (người phi bản ngữ) → 90,06% (TTS). Shell kết luận: **bottleneck nằm ở độ biến thiên phát âm con người, không ở chip** — TTS sạch thậm chí vượt điểm benchmark vì đồng nhất acoustic với dữ liệu native.
2. **Lỗi hệ thống theo cặp từ âm-đại gần nhau**: các cặp nguyên âm giống nhau ("no/go", "off/on") chiếm phần lớn lỗi, đặc biệt với nguyên accents — gợi ý nguyên tắc chọn từ khóa cho KWS **phân biệt âm vị học** (không chọn 2 từ có nguyên âm vần lẫn lộn).
3. **Phân tích ngưỡng tin cậy 0,7** (đóng khít ngưỡng **0,70** dự án dùng!) cho thấy điểm số phụ thuộc ít nhiều vào ngưỡng — nghĩa là: 1,81 điểm với người nói, 0,04 điểm với TTS.

#### 2.1.8. Bảng cấu hình đầy đủ của Medur-2026 — tổng hợp về một chỗ

Bảng này gom toàn bộ tham số bài công bố, để khi hội đồng hỏi về cấu hình cụ thể, ta trả lời được và trả lời đúng phạm vi công bố:

| Hạng mục | Tham số bài công bố | Ghi chú |
|---|---|---|
| Phần cứng | ESP32-S3-EYE: LX7 @ 240 MHz nhân kép; 512 KB SRAM; 8 MB PSRAM; 8 MB flash; micro I2S | Chảy trên chuẩn ESP-IDF V5.0 |
| Dữ liệu | Google Speech Commands V0.02; 105.829 bản ghi 1 s; 2.618 người nói; 12 lớp chuẩn Warden | 10 từ + silence + unknown, các lớp phụ ~10% |
| Đánh giá | 10-fold cross-validation 80/10/10; speaker-independent | Đánh giá ngoài CV: người phi bản ngữ + TTS |
| Tín hiệu | 16 kHz → 8 kHz (FIR 5 tap): windowing 25 ms / hop 20 ms | 50 khung từ 1 giây |
| Đặc trưng | FFT 256; 20 Mel tam giác (300–4000 Hz); log tự nhiên; **DCT-II → 13 MFCC/khung**; C₀ = log-Energy | ma trận 13×50 |
| Mô hình | CNN 2D: 3 khối Conv2D 3×3 (32/64/128) + ReLU + MaxPool → Dense 128 → dropout 0,5 → softmax 12 | 684.172 tham số |
| Lượng hóa | INT8 PTQ (LiteRT); scale 0,359; zero_point 42; model 0,68 MB; FP32 7,9 MB | suy hao < 0,5 điểm |
| Đối soát | BC-ResNet retrain trên cùng MFCC 13×50: INT8 142,9 kB; acc 85,35%; latency 365 ms | 2,5× chậm hơn Model 7 |
| Thời gian thực | FreeRTOS nhân kép; VAD sàn nhiễu thích nghi (2× nền); preroll 200 ms; chốt 400 ms im | |
| Suy luận on-device | 145,19 ± 0,01 ms (chưa gồm thu âm) | TFLM + PSRAM arena 1.000 kB |

#### 2.1.9. Những gì bài Medur-2026 KHÔNG công bố — cần nhớ khi đối thoại hội đồng

Khi bị hỏi sơ nguồn số liệu, cần tách bạch giữa bài chưa nói và bài làm sai:

- **Không kiểm chứng cosine/nghịch phân đơn vị đặc trưng** giữa pipeline Python (huấn luyện) và toán tử C++ trên chip — bài mô tả toán tử tương đương nhưng không có bảng residue/cosine như bài Sensors-2026. Đây là khoảng trống bỏ trống so với chuẩn mực của Sensors-2026.
- **Không đo độ trễ khâu MFCC/DSP trên chip** — chỉ có latency suy luận riêng (145,19 ms, không gồm thu âm). Không có tốt như bài Sensors-2026 phân mảnh rạch từng khâu (289 vs 2,05 ms).
- **Không đo điện năng** ở trạng thái luôn-bật giám sát hoặc suy luận.
- **Không công bố được accuracy từng lớp** và confusion matrix dạng bảng số đầy đủ (chỉ mô tả lỗi chính "no→go", "off→on").
- **Không có đánh giá open-set Kiểm nếu với "unknown"**: lớp unknown được huấn luyện nhưng không xét xác suất từ chối khi gặp ngewn Word phát lý luận.
- **Không đo FAR/false-wakeup** (tần suất thức nhầm) — chỉ số critique với hệ thống luôn-bật.
- **Không có baseline so để so suy hao đo đa lỗi multi-seed** của từng lần train (chỉ đếm/đo tài nguyên 1 lần).

#### 2.1.10. Câu hỏi có thể gặp về bài 1 và cách trả lời

| Câu hỏi | Câu trả lời ngắn |
|---|---|
| Vì sao chọn Model 7 mà không Model 4 (0,16 MB)? | Model 4 chỉ khi hung điều 8 MB PSRAM + 2 nhân; Platform chấp nhận model 0,68 MB vẫn đủ nhanh; đổi 0,5 MB lấy ~90% acc và độ bền lượng tử |
| Lợi Vorteil chính model 7 soi chỉ số nào? | Độ bền lượng tử (> 0,5 điểm suy hao) + thời gian suy luận 145 ms vs BC 365 ms (2,5× chậm do kernel chưa tối ưu) |
| "no" → "go" cặp lỗi nanh nào?? | Xảy ra với người phi bản ngữ; là đồng ý chọn từ khóa trong KWS phải phân biệt âm vị| | học; đi avec project: chọn từ khóa "mở cửa / đóng cửa" — 2 từ + Trident paired error analysis theo từ Phật tương tự khảo gần như mães |
| accuracy 81,82% có thấp? | Bị hiền hơn vì bộ đánh giá là chừa native trừ native native 18–33 → tay bài báo: phát xét native native/native heard near-matched "silence" | + chú ý: từ khóa bất định bị dễ lỗi auto-target lterl |
| predict confidence 0,7 khiến accuracy giảm? | Trừ threshold-test: người 81,82 → 80,01 (−1,81); TTS 90,06 → 90,02 (−0,04): ngưỡng 0,7 một hạ thấp rất nhẹ, and project cũng dùng ≥ 0,70 cho lớp 1 |

### 2.2. Sensors-2026 — Hệ thống giám sát âm học TinyML nhận tiếng động vật trên vi điều khiển hẹp tài nguyên

#### 2.2.1. Bối cảnh và mục tiêu

Bài toán: giám sát thụ động các loài động vật hoang dã trên cao nguyên Thanh Tạng (hươu môi trắng, linh dương Tây Tạng, lừa kyang, bò yak hoang, báo, báo tuyết). Mục tiêu kỹ thuật khác với Medur-2026 (KWS 12 lớp trên chuẩn Speech Commands): đây là bài toán **phân loại 7 lớp (6 loài + 1 lớp nền hợp nhất)**, nhưng giá trị tham khảo cao vì tác giả giải quyết một cách hệ thống bài toán **chuyển giao mô hình từ máy tính huấn luyện sang chạy thật trên vi điều khiển** — chính là khâu mà Medur-2026 làm trên chip nhưng chưa đưa ra kiểm chứng định lượng.

#### 2.2.2. Nền tảng phần cứng và pipeline thời gian thực

- Nền tảng: **Arduino Nano 33 BLE Sense Rev2** (nRF52840, nhân Cortex-M4F có FPU), micro **PDM tích hợp sẵn trên bo**, lấy mẫu 16 kHz.
- Cửa sổ âm **200 ms (3.200 mẫu)**; khung 256 mẫu, bước 128 (chồng lấp 50%) → **24 khung × 13 hệ số MFCC = vector đặc trưng 312 chiều**; FFT 256 điểm, cửa sổ Hamming, 26 bộ lọc Mel, log tự nhiên, DCT-II.
- **Cơ chế kích hoạt hai tầng:** lọc theo năng lượng RMS để tránh suy luận trên đoạn im lặng (ngưỡng mặc định 300, được soi cháy qua phân tích độ nhạy với ba ngưỡng 200/300/400), kèm **khoảng nghỉ (cooldown) sau suy luận** tránh kích hoạt lặp trên cùng một sự kiện âm.
- **Double-buffer ping-pong** tách việc thu âm khỏi xử lý — kỹ thuật cùng chuẩn với nhân kép FreeRTOS của bài Medur-2026 và của dự án.

#### 2.2.3. Điểm lõi: chuỗi nhất quán đặc trưng giữa PC và vi điều khiển

Đây là **đóng góp mấu chốt của bài**. Vấn đề: MFCC tính bằng librosa trên PC và toán tử C++ tự viết trên chip dễ lệch nhau vì sai khác về scale FFT, cách dựng bộ lọc Mel, cửa sổ trích mẫu, tính log, độ chính xác dấu phẩy động... dẫn đến phân phối đặc trưng lúc huấn luyện khác lúc chạy thật.

Giải pháp gồm ba tầng:
1. **Mirror C++ operator** — toán tử MFCC trên chip được viết lại đúng cấu trúc và đúng từng tham số như quy trình tham chiếu trên PC.
2. **Đồng bộ tham số chuẩn hóa** — trung bình/độ lệch chuẩn của từng chiều đặc trưng, ước lượng trên tập huấn luyện, được xuất ra mảng C++; chip chuẩn hóa (standardize) đặc trưng bằng chính các mảng đó (kèm cơ chế bảo vệ mẫu số cho các chiều có phương sai rất nhỏ).
3. **Kiểm định định lượng** — cùng một đầu vào PCM cố định, so phần dư và độ tương đồng cosine giữa hai pipeline: **cosine = 1,0000; phần dư trung bình tuyệt đối ~ 7,28×10⁻⁷** (đạt sau khi thống nhất scale công suất phổ).

Kết luận kiểm chứng: sau khi hợp nhất cấu hình, hai pipeline tạo ra đặc trưng MFCC gần như trùng khớp tuyệt đối.

#### 2.2.4. Dữ liệu, tiền xử lý và phân tách

- **Quick Clean:** lọc mẫu theo miền đặc trưng — bỏ mẫu chứa NaN và mẫu có hệ số MFCC có giá trị tuyệt đối vượt ngưỡng; phân tích ablation ba cấu hình (không ngưỡng / 128 / 200) và chọn **τ = 200** (giữ đủ 2.250 mẫu huấn luyện và 522 mẫu kiểm tra, đạt chính xác cao nhất).
- **Dữ liệu nhận thức phần cứng (hardware-aware):** một phần tiếng nền được thu **bằng chính micro PDM trên bo**; thí nghiệm chirp chứng minh hai front-end ghi khác nhau cho đáp ứng tần số khác nhau → huấn luyện trên nền được thu bởi chính thiết bị triển khai thu hẹp khoảng phân phối giữa dữ liệu huấn luyện và dữ liệu chạy thật.
- **Phân tách source-isolated:** mẫu cùng một nguồn bản ghi/cùng phiên không được xuất hiện trong cả hai tập huấn luyện và kiểm tra — chặn "rò rỉ dữ liệu" làm chỉ số kiểm tra quá lạc quan. Tỷ lệ cuối: mỗi lớp loài 270 huấn luyện/42 kiểm tra; lớp nền 630/270; tổng 2.250/522.

#### 2.2.5. Mô hình và kết quả

Mô hình triển khai là **MLP gọn 312 → 64 → 32 → 7** (ReLU, softmax), bộ tối ưu Adam, early stopping; so sánh với các baseline: Decision Tree, Random Forest, SVM-RBF, KNN, và một **CNN nhẹ trên ma trận 24×13**.

| Mô hình | Test Accuracy (%) / Test Macro-F1 (%) | Vai trò |
|---|---|---|
| Random Forest | 99,04 / 98,29 | baseline PC, không triển khai được |
| SVM-RBF | 98,66 / 97,60 | baseline PC |
| **MLP (đề xuất)** | **98,28 / 97,21** | **INT8, triển khai trên MCU** |
| KNN (k=5) | 96,74 / 96,32 | baseline PC |
| CNN nhẹ | 92,15 / 88,45 | baseline, thấp hơn MLP |

Phân tích ổn định trên 10 hạt giống ngẫu nhiên (multi-seed): **98,64% ± 0,26% accuracy và 97,87% ± 0,38% macro-F1** — chứng minh không phụ thuộc vào một lần chạy may mắn. Kết luận phương pháp quan trọng: chọn mô hình triển khai **không theo accuracy cao nhất trên PC** mà theo **khả năng chuyển đổi INT8, bộ nhớ và thời gian suy luận** — chấp nhận chỉ số không cao nhất (thua Random Forest) để đổi lấy triển khai được thật.

#### 2.2.6. Tài nguyên, độ trễ và điện năng

| Chỉ số | Giá trị |
|---|---|
| Mô hình INT8 | 27.528 B (~26,9 KB) |
| Flash firmware | 374.608 B (38%) |
| SRAM biến toàn cục | 151.312 B (57%) |
| Độ trễ hậu cửa sổ | **~303 ms** |
| Phân mảnh độ trễ | MFCC ~289 ms; **TFLM chỉ ~2,05 ms** |
| Công suất đầu vào | 0,783–0,825 W |
| Tự chủ (pin 3,7 V/2 Ah, hiệu suất 0,85) | 7,63–8,03 giờ |

**Kết luận tinh tế đáng học:** điểm nghẽn nằm ở **trích đặc trưng MFCC (289 ms)** chứ không phải mạng nơ-ron (2 ms) — giảm kích thước mô hình không giúp tăng tốc hệ thống nếu không tối ưu tính toán MFCC. Đây chính là điểm bài Sensors-2026 "đặt tên" cho nút thắt mà bài Medur-2026 **đo nhưng chưa phân mảnh** (chỉ đo latency suy luận 145 ms, không tách MFCC).

#### 2.2.7. Phân tích open-set (thành thật khoa học — đáng học theo)

Với âm không nằm trong 7 lớp đã huấn luyện (vỗ tay, gõ phím, gõ cửa, chuông điện thoại, huýt sáo): **60,39% cửa sổ được gán đúng lớp nền, nhưng 39,61% bị gán nhầm sang một trong 6 lớp mục tiêu, và 26,40% trong số đó có độ tin cậy softmax ≥ 0,90**. Tác giả tự kết luận: hệ thống là bộ phân loại **closed-set 7 lớp**, không phải hệ thống open-world — lớp nền KHÔNG đồng nghĩa với từ chối hoàn toàn đầu vào ngoài phân phối. Hiện tượng này tương tự chính xác rủi ro "người lạ nhận được điểm cao" của mô hình một-người trong dự án chúng ta — rủi ro false-wakeup mà bài Medur-2026 cũng chưa định lượng cho KWS "unknown".

---

#### 2.2.8. Bảng cấu hình đầy đủ của Sensors-2026 — tổng hợp về một chỗ

| Hạng mục | Tham số bài công bố | Ghi chú |
|---|---|---|
| Thu âm | PDM trên bo, 16 kHz; cửa sổ 200 ms (3.200 mẫu) | nRF52840, Cortex-M4F |
| Framing | khung 256 mẫu, hop 128 (chồng 50%) ra 24 khung mỗi cửa sổ | |
| Phổ | FFT 256 điểm, cửa sổ Hamming | |
| Mel | 26 bộ lọc, log tự nhiên | |
| DCT | DCT-II ra 13 hệ số mỗi khung | 24 khung x 13 = 312 chiều |
| Chuẩn hóa | mean/std từng chiều từ tập huấn luyện, xuất sang mảng C++ | có cơ chế chống chia cho phương sai rất nhỏ |
| Lọc sạch dữ liệu | Quick Clean, ngưỡng tau = 200 (ablation: không dùng / 128 / 200) | |
| Gate trước suy luận | RMS-trigger (mặc định 300; ablation 200/300/400) + cooldown | |
| Đồng xử lý | double-buffer ping-pong | tách thu khỏi xử lý |
| Mô hình | MLP 312 - 64 - 32 - 7, ReLU, softmax; Adam; early stopping | |
| Lượng hóa | INT8 chuẩn; mô hình 27.528 B (khoảng 26,9 KB) | |
| Tài nguyên | Flash 374.608 B (38%); SRAM toàn cục 151.312 B (57%) | |
| Thời gian | khoảng 303 ms mỗi cửa sổ; MFCC 289 ms; TFLM 2,05 ms | |
| Điện | 0,783-0,825 W; tự chủ 7,6-8,0 giờ (3,7 V/2 Ah, hiệu suất 0,85) | |

#### 2.2.9. Các thí nghiệm đối chứng của bài 2 — mỗi lựa chọn đều có thí nghiệm

| Thí nghiệm | Biến số | Kết quả / quyết định |
|---|---|---|
| Quick Clean | ngưỡng: không dùng / 128 / 200 | Chọn 200: giữ 2.250 huấn luyện + 522 kiểm tra, accuracy cao nhất |
| RMS trigger | 200 / 300 / 400 | Mặc định 300; phân tích độ nhạy ba ngưỡng |
| Baseline | Decision Tree / Random Forest / SVM-RBF / KNN / CNN nhẹ | MLP thắng theo tiêu chuẩn triển khai |
| Multi-seed | 10 hạt ngẫu nhiên | 98,64 ± 0,26 accuracy; 97,87 ± 0,38 macro-F1 |
| Chirp front-end | hai micro khác nhau | Đáp ứng tần số khác nhau nên thu nền bằng chính PDM trên bo |
| Kiểm định MFCC | cùng một PCM cố định | Cosine 1,0000; phần dư MAE ~ 7,28×10⁻⁷ sau khi thống nhất scale |
| Open-set | vỗ tay, gõ phím, gõ cửa, chuông, huýt sáo | 60,39% đúng nền; 39,61% nhầm; 26,40% của nhóm nhầm có confidence trên 0,90 |

### 2.3. Sổ tay tra nhanh số liệu — trả lời tức thì trong phòng phản biện

| Số liệu | Bài 1 (Medur-2026) | Bài 2 (Sensors-2026) |
|---|---|---|
| Accuracy lab | 89,58% (INT8 0,68 MB; suy hao < 0,5 điểm) | 98,28% (multi-seed 98,64 ± 0,26) |
| Accuracy thực địa | 81,82% (13 phi bản ngữ); 90,06% (TTS 10 giọng) | không đánh cùng dạng |
| F1 | 0,9037 (lab) / 0,8229 (người) | macro-F1 97,21% (multi-seed 97,87 ± 0,38) |
| Mô hình | CNN 2D 684.172 tham số, INT8 0,68 MB | MLP 26,9 KB INT8 |
| Latency suy luận | **145,19 ± 0,01 ms** | 2,05 ms (MFCC riêng 289 ms) |
| Latency toàn chuỗi | không phân mảnh (thu âm không gồm) | ~303 ms |
| Năng lượng | không đo | 0,78–0,83 W; ~8 giờ tự chủ |
| MFCC on-device | Được làm (toán tử C++ không cosine-check) | Có mirror C++ cosine ≈ 1 |
| Lỗi hệ thống | cặp từ mình giống: no→go 18,4% số lỗi; off→on | chỉ thấy trong open-set: 39,61% nhầm, 26,40% conf ≥ 0,9 |

---

## 3. ĐÁNH GIÁ PHÊ PHÁN TỪNG BÀI BÁO

### 3.1. Đánh giá Medur-2026

**Điểm mạnh:**

- Là bài **đối chiếu trực kế tinh thần (hardware-equal) cho dự án**: cùng nền ESP32-S3 (8 MB PSRAM, nhân kép LX7), cùng micro I2S, cùng khung FreeRTOS đa nhân, cùng chuẩn MFCC 13 hệ số/khung và DCT-II.
- Là một trong rất ít bài cung cấp **so sánh có kiểm soát trên thiết bị thật** đối chiếu kiến trúc đề xuất với kiến trúc chuẩn hiện đại (BC-ResNet, retrain trên cùng định dạng đặc trưng) — không bằng nói với bằng số: độ bền lượng tử 0,5 điểm vs 4,4 điểm; latency 145 ms vs 365 ms (2,5×).
- Có **đánh giá hai tầng giữa lab và thực địa** (13 phi bản ngữ + 10 giọng TTS) — điều rất ít bài KWS công bố đồng thời; đo được chính "khoảng cách môi trường âm học".
- Cùng tinh thần **phân tích ngưỡng tin cậy** (0,7) — gắn trực tiếp với ngưỡng 0,70 dự án dùng; định lượng được cái giá của việc đòi conf ≥ 0,7.
- Giải thích rõ cơ chế "hạ dimension đặc trưng để giảm arena + MAC" (13 MFCC @ 8 kHz vs 40 spectral @ 16 kHz) — tư duy thiết kế đúng đắn cho MCU.

**Điểm yếu phương pháp luận:**

- **Không có kiểm chứng cosine đặc trưng PC↔MCU**: bài mô tả mapping toán tử (FIR 5-tap thay FFT-resample SciPy, Hann 25 ms, 20 Mel, DCT-II...) nhưng không công bảng/giá trị residue hay cosine như chuẩn của Sensors-2026. Pipeline chip "được cho là tương đương" nhưng chưa được chứng minh khớp số.
- **Liên quan độ trễ MFCC on-device**: chưa phân mảnh thời gian DSP của.pipeline thời gian thực; chỉ nêu latency suy luận 145,19 ms (đã loại phần thu âm) mà hy vọng đọc cuối làm người referee nhầm "toàn chuỗi". Người đọc cần thận trọng.
- **Không đo điện năng / không đo false-wakeup rate** — với hệ SKU luôn-bật, cả hai chỉ số đều cốt lõi.
- **Không công bố confusion matrix dạng bảng đầy đủ** (chỉ trích 2 cặp lỗi chính), rất khó tái lập phân tích per-class.
- accuracy 81,82% ở tầng "người thật" — thấp đáng so đối con số lab; đúng bài trung thực công bố, nhưng nhấn mạnh khoảng cách 8,2 điểm là do dataset native, **đây chính là cảnh báo: ngdata khác miền đê/thứ tự giữa closed-set và open-world cứuar ta chưa chấp nhận được**.
- Dataset tự thu offline của không có nhiều mẫu nhưng giới hạn địa dư người nói — **không học thị giác cross-locale** như Speech Commands.

**Tổng hợp:** giá trị lớn nhất của Medur-2026 nằm ở **thực chiến phần cứng** và **ba nguyên tắc triển khai**: (i) độ bền lượng tử + measured latency mới là tiêu chuẩn chọn kiến trúc (không phải size); (ii) nhân kép FreeRTOS + VAD sàn nhiễu thích nghi + preroll — kiến trúc thời gian thực chuẩn; (iii) định lượng khoảng lab–thực bằng thí nghiệm người + TTS.

### 3.2. Đánh giá Sensors-2026

**(không đổi so bản trước — giữ nguyên phần 2.2 của bản trước)**

**Điểm mạnh:**
- Chuẩn hóa phương pháp luận: mỗi lựa chọn đều có thí nghiệm sau nó — ablation ngưỡng Quick Clean, ablation ngưỡng RMS trigger, so sánh 5 baseline + CNN, multi-seed 10 lần.
- Giải quyết vấn đề mà hầu hết các bài TinyML audio bỏ qua: **nhất quán đặc trưng PC với MCU**, kèm kiểm chứng định lượng (cosine 1,0000; MAE ~ 7,28×10⁻⁷) và thí nghiệm chirp chứng minh hai front-end micro khác nhau cho phổ đáp ứng khác nhau.
- Phân tách source-isolated chống leakage; dùng macro-F1 cân bằng lớp cho bộ dataset có lớp nền được mở rộng.
- Đo lường triển khai đầy đủ: flash/SRAM/kích thước mô hình INT8/latency phân mảnh theo từng thành phần/**một điểm chi tiết Medur-2026 chưa làm**/công suất/ước tính pin — góc nhìn hệ thống, không chỉ mạng nơ-ron.
- Thành thật về giới hạn: mục open-set công bố chính kết quả không tốt của chính mình — đúng tinh thần khoa học.

**Điểm hạn chế:**
- Quy mô dataset khiêm tốn (mỗi loài 312 mẫu, 522 mẫu kiểm tra) — tác giả tự dè dặt về khả năng tổng quát hóa.
- Mô hình triển khai (MLP) không có chỉ số tốt nhất trên PC — hợp mục tiêu nhưng là lựa chọn "triển khai được" thay vì "chính xác nhất".
- Độ trễ 303 ms (MFCC 289 ms) phản ánh chip Cortex-M4F không có lệnh DSP SIMD như ESP32-S3 — bài báo nhận diện đúng nghẽn nhưng chưa tối ưu được tiếp.
- Công suất 0,78 W ở chế độ giám sát chưa áp dụng duty-cycling/low-power sleep — xếp vào tương lai, chưa phải sản phẩm dùng thật.

**Tổng hợp:** Sensors-2026 là **mẫu chuẩn về phương pháp luận TinyML audio** — ưu tiên đo lường thật và kiểm chứng thay vì chỉ điểm số trên PC.

---

## 4. SO SÁNH TRỰC TIẾP HAI BÀI BÁO

### 4.1. Bảng so sánh tổng hợp

| Tiêu chí | Medur-2026 | Sensors-2026 |
|---|---|---|
| Bài toán | KWS 12 lớp (10 từ + lạ + im) | Phân loại 7 lớp âm học (6 loài + nền) |
| Nền tảng MCU | ESP32-S3-EYE (LX7 ×2 @ 240 MHz, 512 KB SRAM, 8 MB PSRAM) | Arduino Nano 33 BLE Rev2 (Cortex-M4F, nRF52840) |
| Micro | I2S tích hợp trên bo | PDM có sẵn trên bo |
| Trích đặc trưng | on-device (toán tử C++ đơn giản hóa) | on-device mirror C++ + kiểm chứng cosine 1,0000 |
| Đặc trưng | 13 MFCC @ 8 kHz, 50 khung → 13×50; 20 Mel; FFT 256; log tự nhiên; DCT-II; C₀ log-Energy | 24 khung × 13 MFCC = 312-D; 200 ms; FFT 256; Hamming; 26 bộ lọc Mel |
| Mô hình | CNN 2D 684K tham số, softmax 12 | MLP 312→64→32→7 softmax |
| Lượng hóa | INT8 PTQ 0,68 MB (suy hao < 0,5 điểm); BC-ResNet: 142,9 kB nhưng suy hao 4,4 điểm | INT8 chuẩn, 27,5 KB; chọn theo "triển khai được" |
| Latency suy luận | **145,19 ms** (đo riêng, không gồm thu âm) | 2,05 ms |
| Latency MFCC | không tách trong báo cáo | **289 ms** — nút thắt chính |
| Đánh giá | 10-fold CV speaker-independent + 13 người phi bản ngữ + 10 giọng TTS | Source-isolated + multi-seed + ablation từng tham số |
| Open-set | có lớp "unknown" nhưng chưa phân tích tỷ lệ từ chối | phân tích open-set **công bố chính**: 39,61% nhầm lớp, 26,40% conf ≥ 0,9 |
| Năng lượng | không đo | 0,78–0,83 W + tự chủ pin |
| Giá trị tham khảo | Đối chiếu phần cứng trực tiếp + nguyên tắc chọn kiến trúc theo latency/độ bền lượng tử | Chuẩn mẫu phương pháp luận + kiểm chứng đặc trưng |

### 4.2. Điểm hội tụ — chuẩn chung của TinyML audio

1. **MFCC vẫn là lựa chọn đặc trưng mặc định** trên MCU (cả hai bài: 13 hệ số/khung, DCT-II, một số cấu hình thay C₀ bằng log-Energy; khung VAD hai tầng) — khi tài nguyên bị chặn ở vài trăm KB SRAM, MFCC vẫn nén gọn, giải thích được và dễ kiểm tra.
2. **INT8 + TFLM/LiteRT là đường ống chuẩn** — hai bài đều dùng INT8 PTQ trong triển khai — cấu hình mặc định, không còn là sáng tạo.
3. **Cần một tầng lọc trước suy luận** (VAD): bài 1 VAD sàn-nhiễu-thích-nghi (2× nền, preroll 200 ms, post-quiet 400 ms); bài 2 RMS-trigger + cooldown.
4. **Kiến trúc tách thu âm khỏi xử lý**: bài 1 FreeRTOS nhân kép; bài 2 double-buffer ping-pong.
5. **Đánh giá phải chống leakage**: bài 1 dùng speaker-independent CV; bài 2 source-isolated + multi-seed.
6. **Phân tích ngưỡng tin cậy**: bài 1 quét conf ≥ 0,7 (người 81,82→80,01; TTS 90,06→90,02); bài 2 trích confidence trên open-set.

### 4.3. Điểm phân kỳ — thứ quyết định "tính khoa học"

Khoảng cách chất lượng giữa hai bài không nằm ở con số chính xác, mà ở **tính chặt chẽ của việc kiểm chứng giả định**:

- Medur-2026 **thắng ở phần cứng**: so sánh trên chip thật và định lượng khoảng lab–thực địa; nhưng dừng ở mức "toán tử trên chip tương đương về cấu trúc" — không kiểm chứng số giữa pipeline hai miền (PC/MCU), không phân mảnh thời gian MFCC, không đo điện năng.
- Sensors-2026 **thắng ở phương pháp luận**: kiểm chứng định lượng đặc trưng, source-isolated, multi-seed, ablation từng tham số, đo năng lượng thật, và công khai cả kết quả "không tốt" (open-set).
- Hai bài bổ sung nhau: bài 1 cho thấy "làm được trên nền chip mà dự án đang dùng" và định lượng khoảng lab–thực địa; bài 2 là chuẩn mực kiểm chứng và đo lường hệ thống — ghép cả hai cho khung phương pháp luận hoàn chỉnh.

---

## 5. SO SÁNH VỚI LỚP GIỌNG NÓI CỦA DỰ ÁN

### 5.1. Khái quát lớp giọng nói của dự án (theo báo cáo nội bộ)

Lớp giọng nói của dự án chạy trên **cùng chassis phần cứng bài Medur-2026**: ESP32-S3 (8 MB PSRAM), thu 1 giây 16 kHz từ INMP441 (I2S), khuếch đại ×4; lọc VAD (RMS > 30, peak > 100, độ nhạy chỉnh qua web); **trích đặc trưng kiểu MFCC ngay trên thiết bị** (FFT 512 điểm, cửa sổ Hann); hai nhánh:

| | Nhánh 1 (Edge Impulse, chuẩn học thuật) | Nhánh 2 (bare-metal C++ tối ưu tốc độ) |
|---|---|---|
| Bộ lọc Mel | **32 thang Mel tam giác** | 13 dải Mel approximate, từng dải 19 bins |
| Biến đổi cuối | **DCT-II → 13 MFCC/khung** | Log-Energy (không qua DCT) |
| Tensor | **31×13 = 403 chiều** | 32×13 = 416 chiều |
| Mô hình | CNN 1D INT8, **978 tham số** (Conv1D 8 → Conv1D 16 → Flatten 128 → Dense 2; ~16,1 K MAC) | CNN 2D INT8, ~13,601 tham số |
| Flash / RAM | INT8 file 5.920 B (~5,8 KB); **RAM suy luận EON 3.432 B** (giảm từ FP32 interpreter 5.208 B, −34,1%) | ~12 KB INT8; tensor arena (~40 KB) trên PSRAM |
| Suy luận | **1–3 ms** (EON compiler) với budget 100 ms (dư ~8–17×) | chạy liên tục ở STANDBY |
| Accuracy validation | **83,33%** (F1-weighted 0,84; FP32→INT8 suy hao 0 điểm; hội tụ từ epoch 8) | — |

lượng hóa INT8 **đọc trực tiếp scale/zero_point từ file mô hình**; điểm khớp ≥ 0,70 (điều chỉnh runtime) đánh thức lớp khuôn mặt — **giọng chỉ là lớp một; cửa chỉ mở khi cả hai cùng vượt qua trong cùng một phiên 10 giây**.

### 5.2. Bảng so sánh ba chiều

| Tiêu chí | Dự án | Medur-2026 | Sensors-2026 |
|---|---|---|---|
| Loại bài toán | Xác thực sinh trắc một-người (lớp 1 của hệ 2 lớp) | KWS nhận từ khóa 12 lớp | Phân loại 7 lớp âm học |
| Nền tảng | ESP32-S3, 8 MB PSRAM | ESP32-S3-EYE, 8 MB PSRAM | Cortex-M4F, 256 KB SRAM |
| MFCC | **chạy on-device** (FFT 512, Hann) | on-device (toán tử 5-tap FIR + 20 Mel + DCT-II) | Mirror C++ on-device; kiểm chứng cosine 1,0000 |
| Kích thước đặc trưng | 31×13 (EI) / 32×13 (bare-metal) | 13×50 @ 8 kHz | 24×13 = 312-D @ 16 kHz |
| Mô hình | CNN 1D 978 tham số / CNN 2D ~13,6K | CNN 2D 684K | MLP |
| Suy luận | **1–3 ms** (EON) | 145,19 ms (TFLM) | 2,05 ms (TFLM) |
| Gate trước suy luận | VAD RMS + peak | VAD sàn nhiễu thích nghi + preroll 200 ms | RMS-trigger + cooldown |
| Ngưỡng quyết định | 0,70 (điều chỉnh runtime qua web) | phân tích conf 0,7 (−1,81 điểm với người, −0,04 điểm TTS) | argmax softmax (7 lớp) |
| Đánh giá | 83,33% validation nội bộ; **chưa test độc lập chính thức** | 89,58% lab; 81,82% người phi bản ngữ; 90,06% TTS | 98,28%; multi-seed 98,64 ± 0,26 |
| Năng lượng | chưa đo | chưa đo | có, phân mảnh |

### 5.3. Điểm dự án đã vượt trước cả hai bài báo

**Thứ nhất — suy luận nhanh hơn hẳn cả hai bài.** Bài 1: 145,19 ms cho model 684K tham số trên TFLM (sử dụng mở rộng arena PSRAM); bài 2: 2,05 ms cho MLP trên M4. Dự án: **1–3 ms** cho CNN 1D 978 tham số bằng **EON compiler** + ESP-NN ánh xạ MAC INT8 lên lệnh PIE của LX7. Suy luận trên thiết bị của dự án **dư tài nguyên lớn** (so với ngân sách 100 ms), — nghẽn thật sự nằm ở DSP mà cả hai bài báo đều chạm tới; đối chiếu trên cùng nền ESP32-S3: bài 1 suy luận 145 ms, dự án 1–3 ms.

**Thứ hai — tích nhỏ nhưng toàn pipeline âm on-device với hai nhánh.** Cả hai bài báo đều phải "tinh chỉnh" tiếp pipeline MFCC on-device (bài 1: FIR 5-tap, bài 2: mirror C++); dự án có **hai nhánh đặc trưng song song** — chuẩn học thuật 32 Mel + DCT-II (EI) và nhánh approximate bare-metal tối ưu tốc — và đã ghi nhận **FP32→INT8 suy hao 0 điểm** cho CNN 978 tham số — minh chứng lượng tử hóa an toàn cho mạng rất nhỏ.

**Thứ ba — xác thực đa phương thức.** Medur-2026 là KWS thuần từ khóa; Sensors-2026 là phân loại âm. Dự án đã triển khai **giọng + khuôn mặt với cửa sổ 10 giây** — bù đắp một phần rủi ro **chống giả mạo giọng** mà cả hai bài báo đều để ngỏ.

**Thứ tư — hướng đến người dùng cuối:** ngưỡng 0,70 chỉnh runtime qua web (Medur 2026 dùng ngưỡng 0,7 cố định chỉ để phân tích); đổi người dùng không cần sửa firmware (scale/zero_point đọc từ model); máy trạng thái 4 trạng thái luôn dẫn về STANDBY, không có tình huống treo; LED phản hồi theo từng khâu — cả hai bài đều chỉ báo kết quả bằng đèn LED thông thường.

### 5.4. Khoảng trống của dự án so với tiêu chuẩn đo lường của hai bài báo

1. **Chưa kiểm chứng nhất quán MFCC giữa PC và firmware** — bài 1 chưa làm khâu này; bài 2 đã làm chuẩn với cosine 1,0000 / MAE 7,28×10⁻⁷. Dự án huấn luyện bằng script Python (Edge Impulse) và chạy đặc trưng on-device — hai pipeline mô tả cùng cấu hình (31–32 khung × 13 dải, FFT 512, Hann) nhưng **chưa có báo cáo định lượng** phần dư / cosine. Nếu có lệch số nhỏ, mô hình vẫn chạy nhưng điểm số bị trượt âm thầm.
2. **Chưa đo latency phân mảnh và đo điện năng như chuẩn của hai bài**: bài 1 có latency suy luận 145,19 ms; bài 2 có bảng phân mảnh (289 vs 2,05 ms) + công suất 0,78 W. Dự án có timeout 1–3 ms suy luận nhưng **chưa có bảng phân mảnh DSP/suy luận P95/max** để đối chiếu trực tiếp.
3. **Chưa có đánh giá thực địa đa người nói như bài Medur-2026 (13 người phi bản ngữ + 10 giọng TTS)**: dự án mới có dataset một người chủ; chưa có bộ kiểm thử **người lạ + giọng tổng hợp** — mà Medur-2026 chứng minh **giọng tổng hợp là môi trường kiểm chứng gần như ideal ở độ được lab** (90,06% ≈ lab) và **giọng người lạ là môi trường khó** (−8,2 điểm). Phép suy cho dự án chính xác: cần đo tỷ lệ người lạ được điểm cao (false accept) và giọng TTS/replay.
4. **Bộ dữ liệu huấn luyện chưa xử lý leakage cùng nguồn**: bài 1 dùng speaker-independent CV; bài 2 source-isolated — nếu chỉ chia train/test ngẫu nhiên trên các mẫu thu liên tiếp, mô hình có thể nhớ "dấu vân âm thanh của buổi thu" thay vì đặc trưng giọng.
5. **Lớp nền / lớp unknown chưa được phân tích hệ thống như Bài 2** (open-set công bố 26,40% conf ≥ 0,9) và chưa định lượng false-wakeup (tỷ lệ thức dậy nhầm) mà hai bài báo đều khuyến nghị đo.

### 5.5. Dự án đã làm trước những gì hai bài báo chỉ đặt vào Future work

| Hướng phát triển trong bài báo | Trạng thái của dự án |
|---|---|
| Medur-2026: "tăng tốc DSP/triệu latency bằng thiết kế luận lực thua size" | **Đã theo triết lý** (EON + 978 tham số + dư 8–17×; mật độ nhất chuẩn quy của latency phân mảnh; tốt như chỉ số Times) |
| Medur-2026: "thu hẹp lab–t thực bằng thí nghiệm người phi bản ngữ + TTS" | Chưa đánh giá trực tiếp (chưa đo người lạ/TTS) nhưng xây đúng chuẩn mực |
| Medur-2026: "kiểm tra độ bền lượng tử khi chọn kiến trúc" | **Đã làm**: FP32→INT8 suy hao 0 điểm (mô hình 978 tham số); nhánh CNN 2D 13,6K chưa đo |
| Sensors-2026: "Kiểm định consistency đặc trưng PC với MCU định lượng" | Chưa |
| Sensors-2026: "Tối ưu tính MFCC để giảm nghẽn đặc trưng" | Đã đi đúng hướng (lệnh DSP LX7 + esp-dsp), chưa benchmark số |
| Sensors-2026: "Đo công suất, duty-cycling" | Chưa đo |
| Sensors-2026: "Chọn mô hình theo khả năng triển khai, không chỉ theo accuracy" | Đã theo triết lý thiết kế (model 12 KB), nhưng chưa có bảng so baseline |

Bảng này cho thấy: **triển khai kỹ thuật của dự án đã vượt hai bài báo đối chiếu ở nhiều mục**, nhưng **khâu đo lường và kiểm chứng khoa học lại thiếu hơn cả bài báo yếu** — đủ để đối chiếu kiến trúc, chưa đủ để đối chiếu con số.

---

## 6. KHUYẾN NGHI CẢI TIẾN CHO DỰ ÁN (theo mức ưu tiên)

### 6.1. Nhóm 1 — Đánh giá chính thức (ưu tiên cao nhất, chi phí thấp)

1. **Thiết lập giao thức đánh giá mô phỏng kết hợp chuẩn của cả hai bài:** bộ kiểm thử gồm (i) mẫu giọng chủ nhà từ các buổi thu **khác với các buổi thu dùng để huấn luyện** (speaker-isolated, chuẩn bài 1), (ii) giọng người lạ (đo false-accept), (iii) âm nền ESC-50 + giọng **TTS** (đo chống giả mạo — mô phỏng đánh giá 10 giọng TTS của bài 1); chạy bằng chính firmware hoặc mô phỏng pipeline mirror trên PC.
2. Báo cáo **Accuracy/Precision/Recall/F1 + confusion matrix + FAR/FRR theo sweep ngưỡng** (từ 0,5 đến 0,95) để chọn ngưỡng 0,70 có căn cứ — Medur-2026 đã đo riêng: áp ngưỡng tin cậy ≥ 0,7 làm giảm 1,81 điểm chính xác; **multi-seed (5–10 lần huấn luyện lại)** như chuẩn bài 2.
3. Trong báo cáo đồ án, **ghi rõ trạng thái "validation nội bộ 83,33%"** — không mở rộng gọi là kết quả kiểm thử độc lập.

### 6.2. Nhóm 2 — Kiểm chứng pipeline (chi phí vừa)

4. **Kiểm định nhất quán đặc trưng theo Sensors-2026:** ghi một PCM cố định, tính MFCC bằng pipeline huấn luyện (EI/PC) và bằng chính đường dẫn firmware, so phần dư/độ tương đồng cosine — chuẩn phấn đấu "cosine ≈ 1; MAE ~ 10⁻⁷"; nếu có lệch, đối chiếu lại công thức chuẩn hóa/precision như bài 2.
5. **Benchmark thời gian phân mảnh theo chuẩn bài 2 + bài 1:** đo riêng **thời gian DSP/MFCC** (bài 1: 145,19 ms suy luận; bài 2: 289 ms MFCC / 2,05 ms TFLM) và **tổng latency của dự án** với P95/max. Kèm scan scale/zero-point của các lớp để giám sát lượng tử hóa khi debug.
6. **Đo công suất** ở hai trạng thái STANDBY (chỉ micro + VAD) và FACE_AUTH (khuôn mặt hoạt động trong cửa sổ 10 giây); kèm ước lượng tự chủ pin theo công thức T = (V × C × η) / P đã đo; tham chiếu chuẩn 0,78–0,83 W bài 2.

### 6.3. Nhóm 3 — Cải thiện mô hình (làm sau khi có số đo)

7. **Tăng dữ liệu đối chiếu để đo "khoảng lab–thực" (bài học chính của bài 1):** bổ sung các buổi thu ở điều kiện xa hơn lab (khoảng cách xa, ồn nền đa dạng). Đây là giá trị mà bài 1 đã định lượng 8,2 điểm (89,58% → 81,82%).
8. **Đánh giá class unknown/false-wakeup:** chọn một nhóm âm nền "từ-là-KT" (tiếng TV có người nói, tiếng gõ, chuông) đo **false-wakeup rate**, đồng thời thử siết ngưỡng có triệt được bao nhiêu.
9. **Thử nghiệm A/B giữa CNN 2D và MLP phẳng** trên cùng dataset — bài 2 phát hiện CNN nhẹ trên ma trận 24×13 **thấp hơn MLP** (92,15% so với 98,28%); bài 1 cho thấy CNN 2D giữ độ bền lượng tử tốt hơn — kiểm chứng A/B rất "rẻ" vì hạ tầng huấn luyện đã có.
10. **Chuẩn hóa quy trình đo thành script** (protocol đánh giá chạy lại được tự động khi có dữ liệu mới) — kế thừa được cho các báo cáo sau.

### 6.4. Nhóm 4 — Định hướng mở

11. Tận dụng hạ tầng đo lường thành **hệ benchmark nội bộ** để tái sử dụng cho các báo cáo tiếp theo và cho phần phản biện.
12. Đánh giá bổ sung một vòng **kiểm thử trong điều kiện âm học môi trường thật** (khoảng cách xa, tiếng ồn nền trung bình) — cả hai bài đều đo trong điều kiện khá kiểm soát (bài 1 thu người 18–33 tuổi ở môi trường sạch; bài 2 thu tại vùng núi giám sát) — điểm mà dự án còn bỏ ngỏ.

---

## 7. KẾT LUẬN

Hai bài báo phân tích đại diện cho **hai nửa bổ sung của cùng một bài toán TinyML audio trên vi điều khiển**. Medur-2026 là **thực chiến phần cứng**: triển khai CNN INT8 0,68 MB trên chính ESP32-S3 mà dự án dùng, chứng minh bằng thí nghiệm đối soát BC-ResNet rằng **độ bền lượng tử và latency đo được mới quyết định kiến trúc — không phải size mô hình**; và định lượng khoảng lab–thực địa bằng thí nghiệm người phi bản ngữ (81,82%) vs TTS (90,06%). Sensors-2026 là mẫu **phương pháp luận chuẩn**: kiểm chứng chéo đặc trưng PC↔MCU định lượng (cosine 1,0000; MAE ~ 7,28×10⁻⁷), đánh giá source-isolated chống leakage, multi-seed, ablation tham số, đo đầy đủ tài nguyên/latency/năng lượng, thành thật về giới hạn open-set, và **đặt tên nút thắt DSP là 95% thời gian (289 ms vs 2,05 ms)**.

So sánh với dự án cho thấy một **đối chiếu trực kế tinh thần nhà nguyên**: dự án tập phần card cùng ESP32-S3 8 MB PSRAM, cùng micro I2S, cùng chuẩn MFCC 13 hệ số/khung, cùng tư duy VAD/luôn-bật, cùng phân tích ngưỡng tin cậy 0,70 — nhưng **đi xa hơn ở pha suy luận (EON compiler, 1–3 ms so với 145,19 ms cùng nền) và đi trước ở kiến trúc hai lớp giọng + khuôn mặt**. Ngược lại, **phần kiểm chứng định lượng (cosine đặc trưng, phân mảnh latency, đo điện năng, đánh giá người lạ/TTS) — dự án chưa có** — chính là phần mà hai bài báo đã thiết lập chuẩn.

Khuyến nghị tổng hợp: hãy **"mượn" quy trình đo lường của Sensors-2026** (source-isolated, multi-seed, ablation, benchmark phân mảnh, đo công suất) và **"mượn" chu trình kiểm thử thực địa của Medur-2026** (đánh giá người nói lạ + giọng tổng hợp + phân tích ngưỡng tin cậy 0,7) áp vào lớp giọng nói của dự án, trước khi tiếp tục thêm tính năng. Trong đó ưu tiên số một là **xây bộ kiểm thử speaker-isolated + người lạ + TTS và công bố bảng chỉ số chính thức** — bước duy nhất biến dự án từ "minh chứng công nghệ" thành "nghiên cứu có số đo có thể so sánh".

Khi thực hiện đủ hai nhóm khuyến nghị 6.1 và 6.2, dự án sẽ sở hữu một bảng chỉ số có thể đặt **song song với bảng kết quả của hai bài báo này trong một trang báo cáo** — đúng chuẩn mực của một nghiên cứu đứng ngang hàng các công trình đã được bình duyệt trong cùng lĩnh vực.

---

## TÀI LIỆU THAM KHẢO

1. Medur, P.; Lubbers, M.; Mauša, G. (2026). *Resource-Constrained Keyword Spotting With Quantized CNNs: Implementation Strategies and Performance Trade-Offs*. International Journal of Intelligent Systems, 2026(1), Article 2317323. DOI: 10.1155/int/2317323. (Nguồn dữ liệu: Google Speech Commands V0.02, Kaggle; giấy phép CC BY 4.0.)
2. Wang, Z.; Yu, G. (2026). *A Sensor-Based TinyML Acoustic Monitoring System for Edge-Side Animal Sound Recognition on Resource-Constrained Microcontrollers*. Sensors, 26(13), 3972. DOI: 10.3390/s26133972.
3. Báo cáo dự án nội bộ: *Báo cáo dự án Edge AI — Khóa cửa thông minh xác thực hai lớp* (docs/BAO_CAO_DU_AN.md), ngày 01/10/2026.
4. David, R.; Duke, J. và cộng sự (2021). *TensorFlow Lite Micro: Embedded Machine Learning for TinyML Systems*. Proceedings of Machine Learning and Systems 3, tr. 800–811.
5. Davis, S.; Mermelstein, P. (1980). *Comparison of parametric representations for monosyllabic word recognition in continuously spoken sentences*. IEEE Transactions on Acoustics, Speech, and Signal Processing, 28(4), 357–366.
6. Warden, P. (2018). *Speech Commands: A Dataset for Limited-Vocabulary Speech Recognition*. arXiv:1804.03209.
7. Kim, B.; Chang, S.; Lee, J.; Sung, D. (2023). *Broadcasted Residual Learning for Efficient Keyword Spotting* (BC-ResNet).
8. Banbury, C. và cộng sự (2021). *MLPerf Tiny Benchmark*. arXiv:2106.07597.

*Số liệu của hai bài báo được trích trực tiếp từ bản gốc: bài 1 từ bản full-text truy xuất trên Wiley Online Library (ngày 26/10/2026); bài 2 từ bản gốc lưu trong thư mục papers/ của dự án.*
