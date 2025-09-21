Samples de CSV mínimos para importadores de Finanzas. Guardar en UTF-8 (con o sin BOM).

Archivos:
- expenses.csv → tools/import_expenses.py
  - Headers principales: Fecha, Categoria, Descripcion, Monto, Moneda, Proveedor_RUT, Proyecto, Fuente, Estado, Comprobante
  - Alternativas aceptadas: categoria/Categoría, glosa/Glosa, monto/Total, RUT/RUT_Proveedor, etc.
- taxes.csv → tools/import_taxes.py
  - Headers: Periodo, Tipo, Debito, Credito, Neto, Estado, FechaPresentacion, Fuente
- previred.csv → tools/import_previred.py
  - Headers: Periodo, RUT_Trabajador, Nombre, RUT_Empresa, Monto, Estado, FechaPago, Fuente
- payroll.csv → tools/import_payroll.py
  - Headers: Periodo, RUT_Trabajador, Nombre, Cargo, Bruto, Liquido, Descuentos, FechaPago, Fuente
- bank_accounts.csv → tools/import_bank_accounts.py
  - Headers: Banco, Cuenta, Moneda, Titular, Alias
- bank_movements.csv → tools/import_bank_movements.py
  - Headers: Fecha, Banco, Cuenta, Glosa, Monto, Moneda, Tipo, Saldo, Referencia, ID

Comandos ejemplo:
- python ofitec.ai/tools/import_expenses.py --csv ofitec.ai/tools/samples/expenses.csv
- python ofitec.ai/tools/import_taxes.py --csv ofitec.ai/tools/samples/taxes.csv
- python ofitec.ai/tools/import_previred.py --csv ofitec.ai/tools/samples/previred.csv
- python ofitec.ai/tools/import_payroll.py --csv ofitec.ai/tools/samples/payroll.csv
- python ofitec.ai/tools/import_bank_accounts.py --csv ofitec.ai/tools/samples/bank_accounts.csv
- python ofitec.ai/tools/import_bank_movements.py --csv ofitec.ai/tools/samples/bank_movements.csv --source SAMPLE

Luego refrescar vistas y verificar:
- python ofitec.ai/tools/create_finance_views.py
- python ofitec.ai/tools/verify_schema.py
