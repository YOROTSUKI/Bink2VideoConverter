import ctypes
from ctypes import Structure, POINTER, c_int, c_uint, c_ulong, c_char_p, c_void_p, byref
import numpy as np


import av


# 加载 Bink 动态库
bink_dll = ctypes.CDLL('./bink2w64.dll')
#ctypes.LibraryLoader

# 定义 Bink 的常量
BINK_SURFACE32RGBA = 6

# 定义结构体
class BINKRECT(Structure):
    _fields_ = [
        ("Left", c_int),
        ("Top", c_int),
        ("Width", c_int),
        ("Height", c_int)
    ]

class BINK(Structure):
    _fields_ = [
        ("Width", c_int),
        ("Height", c_int),
        ("Frames", c_uint),
        ("FrameNum", c_uint),
        ("FrameRate", c_uint),
        ("FrameRateDiv", c_uint),
        ("ReadError", c_uint),
        ("OpenFlags", c_ulong),
        ("FrameRects", BINKRECT),
        ("NumRects", c_uint),
        ("FrameChangePercent", c_uint)
    ]

# 定义 Bink 函数的签名
bink_dll.BinkOpen.argtypes = [c_char_p, c_ulong]
bink_dll.BinkOpen.restype = c_void_p

bink_dll.BinkClose.argtypes = [c_void_p]
bink_dll.BinkDoFrame.argtypes = [c_void_p]
bink_dll.BinkNextFrame.argtypes = [c_void_p]
bink_dll.BinkCopyToBuffer.argtypes = [c_void_p, ctypes.POINTER(ctypes.c_ubyte), c_int, c_uint, c_uint, c_uint, c_ulong]
bink_dll.BinkWait.argtypes = [c_void_p]
bink_dll.BinkWait.restype = c_int

# 打开 Bink 文件
def open_bink(file_path):
    bink = bink_dll.BinkOpen(file_path.encode('utf-8'), 0)
    if not bink:
        raise RuntimeError("Failed to open Bink file.")
    return bink

# 播放 Bink 视频
def play_bink(file_path):
    bink = open_bink(file_path)
    buffer_arrary = []
    output_file_name = file_path.split('\\')[-1].replace('.bik','.mp4')

    try:
        # 获取视频信息
        bink_info = BINK()
        ctypes.memmove(ctypes.byref(bink_info), bink, ctypes.sizeof(BINK))
        width, height = bink_info.Width, bink_info.Height

        # 创建帧缓冲区
        buffer_size = width * height * 4  # RGBA
        buffer = (ctypes.c_ubyte * buffer_size)()

        buffer_arrary = []
        container = av.open(output_file_name, mode='w')

        stream = container.add_stream("h264", rate=30)
        stream.width = width
        stream.height = height
        stream.pix_fmt = "yuv420p" 

        # 播放视频
        while bink_dll.BinkWait(bink) == 0:
            bink_dll.BinkDoFrame(bink)
            bink_dll.BinkCopyToBuffer(bink, buffer, width * 4, height, 0, 0, BINK_SURFACE32RGBA)

            # 将缓冲区转换为图像
            frame_data = np.frombuffer(buffer, dtype=np.uint8).reshape((height, width, 4))
            rgb_frame = frame_data[:, :, :3] 


            frame_av = av.VideoFrame.from_ndarray(rgb_frame, format="rgb24")
            for packet in stream.encode(frame_av):
                container.mux(packet)
            # img = Image.fromarray(frame_data)
            # img.show()

            bink_dll.BinkNextFrame(bink)
        for packet in stream.encode(None):  # 刷新缓冲区
            container.mux(packet)


        container.close()


    finally:
        bink_dll.BinkClose(bink)

# 示例：播放 Bink 视频
play_bink(r"frontend.bik")
