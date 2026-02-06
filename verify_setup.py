import os
import sys

def check_environment():
    print("="*60)
    print("Environment Check")
    print("="*60)
    
    python_version = sys.version
    print(f"Python Version: {python_version}")
    
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        return False
    else:
        print("✅ Python version is compatible")
    
    if os.path.exists('.env'):
        print("✅ .env file exists")
    else:
        print("⚠️  .env file not found. Please copy .env.example to .env and add your API keys")
    
    print()

def check_dependencies():
    print("="*60)
    print("Dependencies Check")
    print("="*60)
    
    required_packages = [
        'crewai',
        'langchain_openai',
        'dotenv'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} is installed")
        except ImportError:
            print(f"❌ {package} is NOT installed")
            missing_packages.append(package)
    
    print()
    
    if missing_packages:
        print(f"Missing packages: {', '.join(missing_packages)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    return True

def check_project_structure():
    print("="*60)
    print("Project Structure Check")
    print("="*60)
    
    required_files = [
        'blog_crew.py',
        'advanced_blog_crew.py',
        'requirements.txt',
        'config/agents.yaml',
        'config/tasks.yaml'
    ]
    
    all_exist = True
    
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file} exists")
        else:
            print(f"❌ {file} is missing")
            all_exist = False
    
    print()
    return all_exist

def main():
    print("\n" + "="*60)
    print("AI Blog Writing Crew - Setup Verification")
    print("="*60 + "\n")
    
    check_environment()
    
    structure_ok = check_project_structure()
    
    deps_ok = check_dependencies()
    
    print("="*60)
    print("Summary")
    print("="*60)
    
    if structure_ok and deps_ok:
        print("✅ All checks passed! You can run the project:")
        print("   - Basic version: python blog_crew.py")
        print("   - Advanced version: python advanced_blog_crew.py")
    else:
        print("⚠️  Some checks failed. Please fix the issues above.")
        if not deps_ok:
            print("   Install dependencies: pip install -r requirements.txt")
        if not structure_ok:
            print("   Ensure all required files are present")
    
    print()

if __name__ == "__main__":
    main()
