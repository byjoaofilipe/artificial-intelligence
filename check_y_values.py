"""
Script Simples: Verificar se Y são valores binários (0 ou 1)
"""

from data_parser import PatientAllocationData
from milp_model import PatientAllocationMILP

print("="*80)
print("VERIFICAÇÃO DOS VALORES DE Y (VARIÁVEIS BINÁRIAS)")
print("="*80)

# Carregar dados
print("\n📂 Carregando dados...")
data = PatientAllocationData('uploads/s0m0.dat')

# Criar e construir modelo
print("🔨 Construindo modelo...")
model = PatientAllocationMILP(data, lambda1=0.5, lambda2=0.5)
model.build_model()

print(f"\n📊 Modelo tem {len(model.y)} variáveis Y")

# Resolver
print("\n🚀 Resolvendo modelo...")
result = model.solve(time_limit=300, threads=4, verbose=False)

if not result:
    print("❌ Modelo não foi resolvido!")
    exit(1)

print(f"✅ Modelo resolvido! Objetivo: {result['objective_value']:.2f}")

# Obter valores das variáveis Y
print("\n" + "="*80)
print("VALORES DAS VARIÁVEIS Y")
print("="*80)

print("\n📋 ANTES DE RESOLVER (definição das variáveis):")
print("   Domínio: {0, 1} (binárias)")
print(f"   Total de variáveis Y: {len(model.y)}")

print("\n📋 DEPOIS DE RESOLVER (valores atribuídos):")

# Contar valores
count_zero = 0
count_one = 0
count_other = 0

y_values = []

for (p, w, d), var in model.y.items():
    value = var.X  # Valor da variável na solução
    y_values.append(((p, w, d), value))
    
    if abs(value - 0) < 1e-6:  # Essencialmente 0
        count_zero += 1
    elif abs(value - 1) < 1e-6:  # Essencialmente 1
        count_one += 1
    else:  # Nem 0 nem 1 (PROBLEMA!)
        count_other += 1

print(f"\n📊 ESTATÍSTICAS:")
print(f"   Total de variáveis Y: {len(model.y)}")
print(f"   Valores = 0: {count_zero}")
print(f"   Valores = 1: {count_one}")
print(f"   Valores ≠ {0,1}: {count_other}")

# Verificar se todas são binárias
if count_other == 0:
    print("\n✅ TODAS AS VARIÁVEIS Y SÃO BINÁRIAS! ✅")
    print("   Todos os valores são exatamente 0 ou 1")
else:
    print("\n❌ ATENÇÃO: Há variáveis Y com valores não-binários!")
    print(f"   {count_other} variáveis têm valores entre 0 e 1")

# Mostrar TODOS os valores de Y
print("\n" + "="*80)
print("VALORES EXATOS DE TODAS AS VARIÁVEIS Y")
print("="*80)

# Separar em Y=0 e Y=1
y_zeros = [(k, v) for k, v in y_values if abs(v - 0) < 1e-6]
y_ones = [(k, v) for k, v in y_values if abs(v - 1) < 1e-6]
y_others = [(k, v) for k, v in y_values if abs(v - 0) >= 1e-6 and abs(v - 1) >= 1e-6]

print(f"\n1️⃣  VARIÁVEIS Y = 1 (paciente ALOCADO):")
print(f"   Total: {len(y_ones)}")
print(f"   (Estas representam as alocações escolhidas)")
print()

for (p, w, d), value in sorted(y_ones):
    patient = data.patients[p]
    print(f"   Y[{p}, {w}, dia{d}] = {value:.10f}")
    print(f"      └─ Paciente {p} admitido em {w} no dia {d}")
    print(f"      └─ Especialização: {patient['specialization']}, LOS: {patient['los']} dias")

print(f"\n2️⃣  VARIÁVEIS Y = 0 (paciente NÃO alocado nesta opção):")
print(f"   Total: {len(y_zeros)}")
print(f"   (Mostrando apenas as primeiras 20 para não poluir)")
print()

for (p, w, d), value in y_zeros[:20]:
    print(f"   Y[{p}, {w}, dia{d}] = {value:.10f}")

if len(y_zeros) > 20:
    print(f"   ... e mais {len(y_zeros) - 20} variáveis Y = 0")

if y_others:
    print(f"\n3️⃣  VARIÁVEIS Y COM VALORES FRACIONÁRIOS (PROBLEMA!):")
    print(f"   Total: {len(y_others)}")
    print()
    
    for (p, w, d), value in y_others:
        print(f"   ⚠️  Y[{p}, {w}, dia{d}] = {value:.10f}  ← NÃO É BINÁRIO!")

# Verificação final
print("\n" + "="*80)
print("VERIFICAÇÃO FINAL")
print("="*80)

if count_other == 0 and count_one == len(data.patients):
    print("\n✅ PERFEITO!")
    print(f"   • Todas as {len(model.y)} variáveis Y são binárias (0 ou 1)")
    print(f"   • Exatamente {count_one} variáveis Y = 1 (um por paciente)")
    print(f"   • {count_zero} variáveis Y = 0 (opções não escolhidas)")
    print("\n   O modelo está correto! ✨")
elif count_other == 0:
    print("\n⚠️  TODAS as variáveis Y são binárias, MAS:")
    print(f"   • Esperávamos {len(data.patients)} variáveis Y = 1")
    print(f"   • Encontrámos {count_one} variáveis Y = 1")
    print("   • Pode haver um problema na solução")
else:
    print("\n❌ PROBLEMA!")
    print(f"   • {count_other} variáveis Y têm valores fracionários")
    print("   • As variáveis deveriam ser estritamente 0 ou 1")
    print("   • O solver pode não ter encontrado solução inteira")

print("\n" + "="*80)
print()
