from src.memory_local import LocalMemoryClient
import asyncio

USER = 'yash'

async def add_info(text: str, username: str = USER) -> None:         
    async with LocalMemoryClient() as client:                        
        await client.add([{"role": "user", "content": text}],        
        user_id=username)                                                    
        print("[add_info]: information added")      

async def search_info(query: str, username: str = USER, doc_limit:int=5) -> None:                                                                   
    async with LocalMemoryClient() as client:                        
        results = await client.search(query, user_id=username, limit=doc_limit)       
        memories = results.get("results", [])                        
        print(f"[search_info]: {len(memories)} result(s) for '{query}'")                                                           
        for m in memories:                                           
            print(f"  - [{m.get('id', '')[:8]}] {m.get('memory', '')}")               


async def get_all(username: str = USER) -> None:                     
    async with LocalMemoryClient() as client:                        
        results = await client.get_all(user_id=username)             
        memories = results.get("results", [])                        
        print(f"[get_all]: {len(memories)} memory(s) for user+'{username}'")                                                       
        for m in memories:                                           
            print(f"  - [{m.get('id', '')[:8]}] {m.get('memory', '')}")                                                            
                                                                  
async def delete_all(username: str = USER) -> None:                  
    async with LocalMemoryClient() as client:                        
        await client.delete_all(user_id=username)                    
        print(f"[delete_all]: cleared all memories for '{username}'")         



txt = """Right now I am too confused with my career because I am juggling with my part-time job and also I am trying to find a job in the UK but the problem is that the UK job market is too tough. I'm not able to get any interview calls or any phone calls from interviewers, or any agencies or any companies from the UK.
        Now I am getting confused about whether I'm going in the right direction or the wrong direction. I am completely lost in the middle of the way. What I should do I really don't know. I'm really much interested in becoming an AI engineer. The problem is that sometimes I doubt myself about whether I have proper or 
        good knowledge about this field or whether I can prove myself in this field. I'm really lost. And also I'm too confused right now and I don't know what to do. Moving forward whether I should apply for a data scientist role or whether I should apply for the AI engineering role. I am completely lost because if I apply for a data scientist role even though they need professionals or they need a more experienced person. The thing is I have some experience but in a research field as well. I did some voluntary work in computer vision but still my profile was AI engineer in London. I also have one year of voluntary work experience from London and five months of experience as a research intern at the University of Stargate. Before that I had a data analytics intern experience in India but still I am lost and I am not able to figure out a way forward."""


if __name__=="__main__":
    # asyncio.run(add_info(txt))
    asyncio.run(search_info(query="what am i is worried about", username=USER))
    