import time
import real_time_agent  # We import your main agent so we use the SAME logic (and popup blocking!)

def force_post_now():
    print("🚨 MANUAL OVERRIDE: Forcing a post RIGHT NOW...")
    
    # 1. Find the best news
    article = real_time_agent.get_best_fresh_article()
    
    if article:
        print(f"📰 Found story: {article['title']}")
        
        # 2. Write the summary
        summary = real_time_agent.get_ai_summary(article['title'], article['summary'])
        final_text = f"{summary}\n\n🔗 {article['link']}"
        
        # 3. Post it using the V4 Logic (with Popup Killer)
        success = real_time_agent.post_to_facebook(final_text)
        
        if success:
            print(f"✅ Success! Added {article['link']} to history.")
            real_time_agent.save_to_history(article['link'])
        else:
            print("❌ Failed to post.")
            
    else:
        print("🤷 No fresh news found to post.")

if __name__ == "__main__":
    force_post_now()