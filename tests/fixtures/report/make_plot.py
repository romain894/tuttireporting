"""Create a tiny vector PDF fixture with only the Python standard library."""
from pathlib import Path

content = b'0.2 0.4 0.6 RG 2 w 30 30 m 80 60 l 140 100 l 220 140 l S'
objects = [
    b'<< /Type /Catalog /Pages 2 0 R >>',
    b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
    b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 250 170] /Contents 4 0 R /Resources << >> >>',
    b'<< /Length ' + str(len(content)).encode() + b' >>\nstream\n' + content + b'\nendstream',
]
data = bytearray(b'%PDF-1.4\n')
offsets = [0]
for i, obj in enumerate(objects, 1):
    offsets.append(len(data))
    data.extend(f'{i} 0 obj\n'.encode() + obj + b'\nendobj\n')
xref = len(data)
data.extend(b'xref\n0 5\n0000000000 65535 f \n')
for offset in offsets[1:]:
    data.extend(f'{offset:010d} 00000 n \n'.encode())
data.extend(f'trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())
path = Path(__file__).parent / 'plots' / 'score2.pdf'
path.parent.mkdir(exist_ok=True)
path.write_bytes(data)
