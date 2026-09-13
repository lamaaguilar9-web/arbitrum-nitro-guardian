# LEGAL SPECIFICATIONS & TERMS OF SERVICE (TÉRMINOS Y CONDICIONES)

**Project:** Arbitrum Nitro Guardian (DeFi AI Circuit Breaker - Arbitrum One L2)  
**Target Architecture:** Arbitrum Nitro / Camelot DEX / GMX v2  
**Governance Framework:** Asymmetric OpenZeppelin AccessControl (PAUSER_ROLE vs UNPAUSER_ROLE)  

---

## 1. INTRODUCCIÓN Y MARCO DE RESPONSABILIDAD

El presente documento establece las condiciones legales, límites de responsabilidad civil y financiera, y especificaciones de seguridad aplicables al software de código abierto **Arbitrum Nitro Guardian**.

Este sistema ha sido diseñado con controles técnicos asimétricos para mitigar riesgos operacionales y salvaguardar la integridad de los protocolos financieros en la red Arbitrum One.

---

## 2. CLÁUSULAS LEGALES OBLIGATORIAS

### [CLÁUSULA DE ESTADO ACTUAL - AS-IS]
> "El software y sus componentes automatizados se proporcionan 'tal cual' ('as-is'), sin garantías explícitas ni implícitas de ningún tipo, incluidas, entre otras, garantías de comerciabilidad, idoneidad para un propósito particular o ausencia de fallos. El proveedor no garantiza que el sistema prevenga, detecte o mitigue la totalidad de ataques, exploits o fallos en los contratos inteligentes monitoreados."

### [CLÁUSULA DE EXCLUSIÓN DE RESPONSABILIDAD POR FALSOS POSITIVOS Y LATENCIA]
> "Bajo ninguna circunstancia el proveedor será responsable de pérdidas directas, indirectas, incidentales, consecuentes o de costo de oportunidad (incluidas, de forma enunciativa pero no limitativa, pérdidas de fondos, fallos de liquidación o interrupción operativa) resultantes de: (a) pausas ejecutadas a causa de falsos positivos o divergencias transitorias del mercado; o (b) la incapacidad del software para ejecutar medidas cautelares debido a congestión de la red, variaciones de gas o fallos de infraestructura de terceros."

### [CLÁUSULA DE PRIVACIDAD Y DATOS]
> "El software opera analizando y transmitiendo exclusivamente datos de dominio público disponibles en la red de bloques (blockchain) y en el feed del secuenciador Nitro. No se recopilan, almacenan ni procesan datos de identificación personal (PII), limitándose cualquier tratamiento a identificadores estrictamente operativos necesarios para el despliegue técnico del servicio."

---

## 3. ESPECIFICACIÓN DE CONTROLES TÉCNICOS Y MITIGACIÓN DE RIESGOS

### A. Prevención de Falsos Positivos (Denegación de Servicio)
* **Riesgo:** Una pausa involuntaria que congele liquidaciones o arbitrajes legítimos.
* **Control Técnico Implementado:**
  1. El contrato inteligente (`ArbitrumNitroCircuitBreaker.sol`) únicamente permite pausas granulares selectivas por pool, jamás congelamiento global del protocolo.
  2. Ningún contrato permite transferir, bloquear o custodiar activos de los usuarios.
  3. Implementación de una ventana máxima de pausa (`MAX_PAUSE_DURATION = 24 hours`) que restablece automáticamente el estado operativo en caso de inacción prolongada.

### B. Seguridad ante Compromiso de Claves Privadas (Mínimo Privilegio)
* **Riesgo:** Extracción o filtración de la clave privada del servidor donde opera el agente centinela.
* **Control Técnico Implementado:**
  1. La clave del agente centinela tiene asignado **únicamente** el rol `PAUSER_ROLE`.
  2. La clave del bot **carece por completo** de permisos para transferir fondos, cambiar gobernanza, actualizar contratos o ejecutar la función `unpausePool()`.
  3. El rol `UNPAUSER_ROLE` y el `DEFAULT_ADMIN_ROLE` están asignados de manera inmutable y exclusiva a un contrato multifirma **Gnosis Safe (3/5)** o timelock de gobernanza descentralizada.

---

## 4. CONTACTO Y GOBERNANZA

* **Entidad Desarrolladora:** DeFi AI Sentinel Security Operations
* **Repositorio Oficial:** https://github.com/lamaaguilar9-web/arbitrum-nitro-guardian
* **Gobernanza Multisig:** Gnosis Safe en Arbitrum One
