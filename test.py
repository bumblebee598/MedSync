import requests

def test_audio_endpoint():
    url = "http://localhost:8000/process-audio"
    
    # Open the audio file
    files = {
        'audio': ('test.mp3', open('test.mp3', 'rb'), 'audio/mpeg')
    }
    
    # Add the gender parameter
    data = {
        'gender': 'woman'
          # or 'man'
    }
    
    # Make the request
    response = requests.post(url, files=files, data=data)
    
    # Save the response audio
    if response.status_code == 200:
        with open('response.mp3', 'wb') as f:
            f.write(response.content)
        print("Successfully saved response audio")
    else:
        print(f"Error: {response.json()}")

def test_pdf_endpoint():
    url = "http://localhost:8000/process-pdf"
    
    # Open the PDF file
    files = {
        'pdf': ('test.pdf', open('.pdf', 'rb'), 'application/pdf')
    }
    
    # Add the metadata parameters
    data = {
        'title': 'Test Document',
        'link': 'https://example.com/test',
        'source': 'Test Source'
    }
    
    # Make the request
    response = requests.post(url, files=files, data=data)
    
    # Print the response
    if response.status_code == 200:
        print("Successfully processed PDF:", response.json())
    else:
        print(f"Error: {response.json()}")

if __name__ == "__main__":
    # Test both endpoints
    print("Testing audio endpoint...")
    # test_audio_endpoint()
    print("\nTesting PDF endpoint...")
    test_pdf_endpoint()