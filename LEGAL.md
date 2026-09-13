# LEGAL SPECIFICATIONS & REGULATORY COMPLIANCE FRAMEWORK
**Project:** Arbitrum Nitro Guardian (DeFi Circuit Breaker L2)  
**Governance Standard:** Asymmetric Least-Privilege & Progressive DAO Decentralization  
**Regulatory Context:** MiCA (EU Markets in Crypto-Assets) / FATF Guidance on Non-Custodial Infrastructure  

---

## 1. MARCO LEGAL INSTITUCIONAL Y NO CUSTODIA

El software **Arbitrum Nitro Guardian** ha sido estructurado para eliminar la calificación de custodia financiera, intermediación fiduciaria o transmisión de dinero (*Money Services Business / CASP*):

1. **Ausencia Total de Métodos de Custodia:**  
   Los contratos inteligentes (`ArbitrumNitroCircuitBreaker.sol`) **carecen de funciones `transfer`, `transferFrom`, `approve` o saldos en depósito**. La función del sistema se limita exclusivamente a emitir señales booleanas operativas (`isOperationPermitted`).
2. **Imposibilidad Técnica de Apropiación:**  
   Ningún operador, bot automatizado ni miembro de la multifirma puede apropiarse, redirigir o bloquear permanentemente los fondos de los usuarios.

---

## 2. VECTOR 5: MITIGACIÓN DE CONTROL FÁCTICO (CUMPLIMIENTO MiCA / GAFI)

Bajo los marcos regulatorios modernos (Directiva MiCA en la UE y directrices del GAFI), las autoridades examinan el **control fáctico** (*de facto control*). Para evitar que la potestad de pausar sea interpretada como administración centralizada de una plataforma financiera:

### A. Limitación de Discrecionalidad (Límite Consecutivo de Pausas)
* El contrato impone una restricción inmutable a nivel de bytecode: **`MAX_CONSECUTIVE_PAUSES = 2`**.
* La clave operativa y la multisig **no pueden ejecutar pausas sucesivas indefinidas** para secuestrar la operativa de un protocolo. Tras 2 pausas consecutivas, el sistema exige una votación de gobernanza o la activación del timelock descentralizado.

### B. Hoja de Ruta hacia la Descentralización Progresiva (DAO Timelock)
1. **Fase 1 (Arranque y Auditoría - Actual):**  
   Gnosis Safe Multifirma 3/5 con miembros del equipo técnico y auditores de seguridad externos. Se utiliza exclusivamente para mitigar exploits durante la fase de despliegue inicial.
2. **Fase 2 (Migración a Gobernanza On-Chain):**  
   El método `transferGovernanceToTimelock(address _daoTimelock)` cede irrevocablemente el rol de administración (`DEFAULT_ADMIN_ROLE`) y el rol de reanudación (`UNPAUSER_ROLE`) a un contrato Timelock de gobernanza de DAO, eliminando cualquier vector de control fáctico por parte de personas físicas identificables.
3. **Criterios Objetivos de Intervención:**  
   La intervención de emergencia no es discrecional ni política: está estrictamente condicionada por el **incumplimiento matemático de invariantes de balance contable** (caída de $k > 30\%$ o ratio colateral/deuda $< 0.65$).

---

## 3. CLÁUSULAS LEGALES OBLIGATORIAS (TÉRMINOS Y CONDICIONES)

### [CLÁUSULA DE ESTADO ACTUAL - AS-IS]
> "El software y sus componentes automatizados se proporcionan 'tal cual' ('as-is'), sin garantías explícitas ni implícitas de ningún tipo, incluidas, entre otras, garantías de comerciabilidad, idoneidad para un propósito particular o ausencia de fallos. El proveedor no garantiza que el sistema prevenga, detecte o mitigue la totalidad de ataques, exploits o fallos en los contratos inteligentes monitoreados."

### [CLÁUSULA DE EXCLUSIÓN DE RESPONSABILIDAD POR FALSOS POSITIVOS Y LATENCIA]
> "Bajo ninguna circunstancia el proveedor será responsable de pérdidas directas, indirectas, incidentales, consecuentes o de costo de oportunidad (incluidas, de forma enunciativa pero no limitativa, pérdidas de fondos, fallos de liquidación o interrupción operativa) resultantes de: (a) pausas ejecutadas a causa de falsos positivos o divergencias transitorias del mercado; o (b) la incapacidad del software para ejecutar medidas cautelares debido a congestión de la red, variaciones de gas o fallos de infraestructura de terceros."

### [CLÁUSULA DE PRIVACIDAD Y DATOS]
> "El software opera analizando y transmitiendo exclusivamente datos de dominio público disponibles en la red de bloques (blockchain) y en el feed del secuenciador Nitro. No se recopilan, almacenan ni procesan datos de identificación personal (PII), limitándose cualquier tratamiento a identificadores estrictamente operativos necesarios para el despliegue técnico del servicio."
