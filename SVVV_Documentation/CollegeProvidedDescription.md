# **Quantum Secure Email Client Application**

\---

Email communication is a fundamental part of modern business and personal interactions. However, conventional encryption mechanisms are susceptible to various threats, including eavesdropping, man-in-the-middle attacks, and data breaches in the post quantum era.

Quantum Key Distribution (QKD) offers an unprecedented level of security by distributing secure keys to two users over a quantum channel and these keys can be used for encryption to achieve unconditional/enhanced security.

The objective is to develop an email client application like Microsoft Outlook (can be named as QuMail) which integrates Quantum Key Distribution (QKD) service with existing email protocols to enhance the security of email communication while maintaining compatibility with widely used email servers (Gmail, yahoo mail etc).

This application interfaces with KM (Key Manager) for getting the quantum keys using APIs (illustrated below), with Email servers through standard protocols to utilize email service facility and with users through GUI for capturing various user inputs.

## Use case Scenario

Users (having quantum keys access through the KM) need to exchange email with attachment over untrusted networks (i.e. internet) and existing email service providers (Gmail, Yahoo mail etc). It is assumed that local key managers at both ends have already generated symmetrical quantum keys at their ends. The participants may start with a key bank of 100 keys, each of size 1Kb at KMs.

## Features

Implemented solutions shall have good modularity to allow easy upgradation KM service and email service login feature.

Three level of security configuration -
a. Level 1- No Quantum security
b. Level 2- Quantum-aided AES- use Quantum keys as seed for AES
c. Level 3- Quantum Secure - use One Time Pad
d. Any other encryption may be given as option

## Challenges

Develop a robust mechanism to seamlessly integrate QKD technology into existing email infrastructure. This includes using a secure key which is distributed using QKD, in existing email communication for encryption while maintaining interoperability. An approach to this problem can be Encryption at application layer can be introduced in email client which will use QKD key.

## Preferred OS

Windows

## Note

The participants can make further assumptions regarding the problem. The features listed here are baseline and do not limit the scope of application development.

