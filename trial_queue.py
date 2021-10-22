import asyncio
from asyncio import queues
import time



def on_message(message):
        print('syncronous call')
        queue = asyncio.Queue()
        asyncio.create_task(process_message(f'worker', queue))
        queue.put_nowait(message)

async def process_message(message,queue):
         message = await queue.get()
         print('asyncio call')
         print(message)
         queue.task_done()

async def main():
        
        
        while True:
            message = 'hello from main'
            on_message(message)
            
            await asyncio.sleep(1)  # wait for duration seconds
        #client.disconnect()


       


if __name__ == "__main__":
    asyncio.run(main())