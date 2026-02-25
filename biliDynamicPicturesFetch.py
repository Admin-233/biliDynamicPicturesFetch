import os
import random
from bilibili_api import user, dynamic, Credential, select_client
import asyncio
import aiohttp
from urllib.parse import urlparse

import pdb

#登录信息
SESSDATA = ""
BILI_JCT = ""
BUVID3 = ""

TargetUID = "3493131167205984"
SAVE_DIR = r"C:\result"

select_client("aiohttp")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
    "Accept": "*/*",
    "Connection": "keep-alive",
}

#分段下载
CHUNK_SIZE = 64 * 1024  # 64KB
MAX_RETRY = 3

async def get_all_dynamics(User: user.User) -> list:
    offset = ""     # 用于记录下一次起点
    dynamics = []   # 用于存储所有动态
    count = 0       #已经获取的页面计数
    
    while True:
        count += 1
        print("Page:", count)
        
        
        #尝试获取动态，重试10次
        max_retry = 10
        retry = 0

        while retry < max_retry:
            try:
                # 获取该页动态
                page = await User.get_dynamics_new(offset)
                break  # 成功就跳出循环
            except:
                retry += 1
                print(f"failed, retry {retry}/{max_retry}")
                
                # 指数退避 + 随机延时
                await asyncio.sleep((2 ** retry) * 0.2 + random.random() * 0.3)
        else:
            # 循环正常结束（没有 break），说明重试 10 次仍失败
            pdb.set_trace()

        dynamics.extend(page["items"])

        if page["has_more"] != 1:
            break
            
        offset = page["offset"] # 设置 offset，用于下一轮循环
        
    return dynamics

async def download_and_modify_time(url, timestamp, save_dir, semaphore, session):#此函数由chatgpt倾情奉献
    async with semaphore:
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path)
        if not filename:
            print("文件名错误")
            return 1

        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, filename)

        if os.path.exists(filepath):
            print("文件重复", filepath)
            return 1

        for attempt in range(1, MAX_RETRY + 1):
            try:
                async with session.get(url, headers=HEADERS) as resp:
                    if resp.status != 200:
                        print("HTTP错误:", resp.status, url)
                        continue

                    # 写入临时文件，防止半截文件污染
                    tmp_path = filepath + ".part"

                    with open(tmp_path, "wb") as f:
                        async for chunk in resp.content.iter_chunked(CHUNK_SIZE):
                            if chunk:
                                f.write(chunk)

                    os.replace(tmp_path, filepath)
                    os.utime(filepath, (timestamp, timestamp))
                    
                    print("完成：", url)
                    return 0

            except (
                aiohttp.ClientPayloadError,
                aiohttp.ClientOSError,
                asyncio.TimeoutError,
                ConnectionResetError,
            ) as e:
                print(f"重试 {attempt}/{MAX_RETRY}:", url, "|", type(e).__name__)

                # 指数退避 + 随机抖动（防风控）
                await asyncio.sleep((2 ** attempt) + random.random())

            except Exception as e:
                print("下载失败:", url, "|", e)
                return 1

        print("最终失败:", url)
        return 1

async def main() -> None:
    
    credential = Credential(sessdata=SESSDATA, bili_jct=BILI_JCT, buvid=BUVID3)
    
    TargetUser = user.User(uid = TargetUID, credential = credential)
    
    result = await get_all_dynamics(TargetUser)
    
    taskList = []   #用于存放下载图片的协程
    
    for i in result:
        if i["type"] != "DYNAMIC_TYPE_DRAW":
            continue
        
        picList = i["modules"]["module_dynamic"]["major"]["opus"]["pics"]
        picTimeStamp = int(i["modules"]["module_author"]["pub_ts"])
        
        sem = asyncio.Semaphore(10) #最多同时下载10个
        timeout = aiohttp.ClientTimeout(total=120)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            taskList = [
                asyncio.create_task(
                    download_and_modify_time(j["url"], picTimeStamp, SAVE_DIR, sem, session)
                )
                for j in picList
            ]
            
            await asyncio.gather(*taskList)

asyncio.run(main())

input("Finished")

#items[?]["modules"]["module_dynamic"]["major"]["opus"]["pics"]
#items[?]["modules"]["module_author"]["pub_ts"]
#items[?]["type"] == DYNAMIC_TYPE_DRAW
#picList[?]["url"]