import uvicorn
import os

if __name__ == "__main__":
    # Ensure uploads directory exists
    if not os.path.exists("uploads"):
        os.makedirs("uploads")
    
    print("Starting ILMA Bot Backend...")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
