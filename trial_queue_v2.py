import asyncio
from asyncio import queues
import time



def on_message(message):
        print('syncronous call')
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(process_message("call from"))

async def process_message(message):
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