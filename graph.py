import matplotlib.pyplot as plt
import io

def create_bar_chart(data, title):
    plt.figure(figsize=(10, 6))
    plt.bar(data.keys(), data.values())
    plt.title(title)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    
    return buf

def create_pie_chart(data, title):
    plt.figure(figsize=(10, 6))
    plt.pie(data.values(), labels=data.keys(), autopct='%1.1f%%')
    plt.title(title)
    plt.axis('equal')
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    
    return buf