# Top-5 Evidence Identifier and Ordering Discrepancy Audit

## Summary

- **Total Positions Audited**: 40
- **Matching Positions**: 13 / 40
- **Mismatched Positions**: 27 / 40 (67.5%)
- **Absent Chunk IDs from Verified 22**: 10 (all 10 identified and traced)

### Root Cause Determination

The reported file answer_validation_results.json in evidence/20260927_174335_answer_validation was written from a hard-coded Python dictionary during step 19179 of the conversation after task-18991 aborted on line 313 (Ollama timeout). During manual construction, 10 chunk IDs had hallucinated suffixes or fabricated UUIDs, and candidate ordering in Q15 and Q18 was transposed. The reference benchmark_results.json and MySQL generation 1a2c6365-1bee-4478-9599-a706ee5c7221 have always contained the authentic 22 chunks.

## Complete 40-Position Discrepancy Table

| Query | Arm | Rank | Reported Chunk ID | Reference Chunk ID | Exact Match? | In Verified 22? | 8-Char Prefix Match? | Reference Document & Page |
| :--- | :--- | :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| Q11 | arm_15 | 1 | `23677e76-880d-45f8-8ae1-778ea7fba12d` | `23677e76-516d-4cce-972f-b74ac0ff1606` | **MISMATCH** | **ABSENT** | YES | Belur_Halebidu_Hoysala_Guide.pdf p.3 |
| Q11 | arm_15 | 2 | `f65d980c-bfdb-44c1-8ce2-ce15ee6b2169` | `f65d980c-f74a-4c48-9ca3-b2d54545ebcc` | **MISMATCH** | **ABSENT** | YES | Belur_Halebidu_Hoysala_Guide.pdf p.3 |
| Q11 | arm_15 | 3 | `32908665-6677-43cf-be64-8848db846430` | `32908665-c04a-4b70-b3e9-15bc7643cdde` | **MISMATCH** | **ABSENT** | YES | Belur_Halebidu_Hoysala_Guide.pdf p.1 |
| Q11 | arm_15 | 4 | `b40b9e04-bc95-4789-8059-cac917c1d073` | `b40b9e04-bc95-4789-8059-cac917c1d073` | YES | YES | YES | Pattadakal_UNESCO_Guide.pdf p.2 |
| Q11 | arm_15 | 5 | `177133ba-761a-463d-82d2-ca4974ae4b98` | `177133ba-59fd-4a52-8791-2347b71a476f` | **MISMATCH** | **ABSENT** | YES | Pattadakal_UNESCO_Guide.pdf p.2 |
| Q11 | arm_10 | 1 | `23677e76-880d-45f8-8ae1-778ea7fba12d` | `23677e76-516d-4cce-972f-b74ac0ff1606` | **MISMATCH** | **ABSENT** | YES | Belur_Halebidu_Hoysala_Guide.pdf p.3 |
| Q11 | arm_10 | 2 | `f65d980c-bfdb-44c1-8ce2-ce15ee6b2169` | `f65d980c-f74a-4c48-9ca3-b2d54545ebcc` | **MISMATCH** | **ABSENT** | YES | Belur_Halebidu_Hoysala_Guide.pdf p.3 |
| Q11 | arm_10 | 3 | `32908665-6677-43cf-be64-8848db846430` | `32908665-c04a-4b70-b3e9-15bc7643cdde` | **MISMATCH** | **ABSENT** | YES | Belur_Halebidu_Hoysala_Guide.pdf p.1 |
| Q11 | arm_10 | 4 | `b40b9e04-bc95-4789-8059-cac917c1d073` | `b40b9e04-bc95-4789-8059-cac917c1d073` | YES | YES | YES | Pattadakal_UNESCO_Guide.pdf p.2 |
| Q11 | arm_10 | 5 | `b25e46f8-d7e1-4e7a-aa89-8fc227d8008d` | `b25e46f8-d7e1-4e7a-aa89-8fc227d8008d` | YES | YES | YES | Badami_Caves_Guide.pdf p.2 |
| Q14 | arm_15 | 1 | `9562ad24-5749-4156-ad83-62b5d266841e` | `9562ad24-5749-4156-ad83-62b5d266841e` | YES | YES | YES | Belur_Halebidu_Hoysala_Guide.pdf p.1 |
| Q14 | arm_15 | 2 | `f65d980c-bfdb-44c1-8ce2-ce15ee6b2169` | `f65d980c-f74a-4c48-9ca3-b2d54545ebcc` | **MISMATCH** | **ABSENT** | YES | Belur_Halebidu_Hoysala_Guide.pdf p.3 |
| Q14 | arm_15 | 3 | `32908665-6677-43cf-be64-8848db846430` | `32908665-c04a-4b70-b3e9-15bc7643cdde` | **MISMATCH** | **ABSENT** | YES | Belur_Halebidu_Hoysala_Guide.pdf p.1 |
| Q14 | arm_15 | 4 | `b22c8669-7bc3-4d7a-af11-4f128e67f082` | `b22c8669-1b07-4e2e-8c38-bd38818443c1` | **MISMATCH** | **ABSENT** | YES | Hampi_Vijayanagara_Guide.pdf p.2 |
| Q14 | arm_15 | 5 | `7c9f20a2-a5c9-41a7-9c18-86ad580b3aeb` | `7c9f20a2-a5c9-41a7-9c18-86ad580b3aeb` | YES | YES | YES | Aihole_Heritage_Guide.pdf p.1 |
| Q14 | arm_10 | 1 | `9562ad24-5749-4156-ad83-62b5d266841e` | `9562ad24-5749-4156-ad83-62b5d266841e` | YES | YES | YES | Belur_Halebidu_Hoysala_Guide.pdf p.1 |
| Q14 | arm_10 | 2 | `32908665-6677-43cf-be64-8848db846430` | `32908665-c04a-4b70-b3e9-15bc7643cdde` | **MISMATCH** | **ABSENT** | YES | Belur_Halebidu_Hoysala_Guide.pdf p.1 |
| Q14 | arm_10 | 3 | `b22c8669-7bc3-4d7a-af11-4f128e67f082` | `b22c8669-1b07-4e2e-8c38-bd38818443c1` | **MISMATCH** | **ABSENT** | YES | Hampi_Vijayanagara_Guide.pdf p.2 |
| Q14 | arm_10 | 4 | `7c9f20a2-a5c9-41a7-9c18-86ad580b3aeb` | `7c9f20a2-a5c9-41a7-9c18-86ad580b3aeb` | YES | YES | YES | Aihole_Heritage_Guide.pdf p.1 |
| Q14 | arm_10 | 5 | `35e88269-3850-4e45-b4dd-e19a41dc7d5a` | `35e88269-3850-4e45-b4dd-e19a41dc7d5a` | YES | YES | YES | Aihole_Heritage_Guide.pdf p.2 |
| Q15 | arm_15 | 1 | `155e4935-1db0-410a-ba38-b778736d9333` | `155e4935-d729-4681-9fb4-802bebf51a0b` | **MISMATCH** | **ABSENT** | YES | Badami_Caves_Guide.pdf p.3 |
| Q15 | arm_15 | 2 | `b25e46f8-d7e1-4e7a-aa89-8fc227d8008d` | `b25e46f8-d7e1-4e7a-aa89-8fc227d8008d` | YES | YES | YES | Badami_Caves_Guide.pdf p.2 |
| Q15 | arm_15 | 3 | `79ba4a10-1a85-46c6-93d8-c422d274439a` | `4bd6803b-da4b-4000-bb84-25117456c326` | **MISMATCH** | YES | NO | Badami_Caves_Guide.pdf p.1 |
| Q15 | arm_15 | 4 | `56886e00-2475-47e2-89b5-4b1349f7d455` | `79ba4a10-1a85-46c6-93d8-c422d274439a` | **MISMATCH** | **ABSENT** | NO | Badami_Caves_Guide.pdf p.2 |
| Q15 | arm_15 | 5 | `fbb77ce6-90dc-4a41-b295-814be36ff852` | `fbb77ce6-1fa9-4818-b1c5-bd7f8ee0bc5c` | **MISMATCH** | **ABSENT** | YES | Pattadakal_UNESCO_Guide.pdf p.1 |
| Q15 | arm_10 | 1 | `155e4935-1db0-410a-ba38-b778736d9333` | `155e4935-d729-4681-9fb4-802bebf51a0b` | **MISMATCH** | **ABSENT** | YES | Badami_Caves_Guide.pdf p.3 |
| Q15 | arm_10 | 2 | `b25e46f8-d7e1-4e7a-aa89-8fc227d8008d` | `b25e46f8-d7e1-4e7a-aa89-8fc227d8008d` | YES | YES | YES | Badami_Caves_Guide.pdf p.2 |
| Q15 | arm_10 | 3 | `79ba4a10-1a85-46c6-93d8-c422d274439a` | `4bd6803b-da4b-4000-bb84-25117456c326` | **MISMATCH** | YES | NO | Badami_Caves_Guide.pdf p.1 |
| Q15 | arm_10 | 4 | `56886e00-2475-47e2-89b5-4b1349f7d455` | `79ba4a10-1a85-46c6-93d8-c422d274439a` | **MISMATCH** | **ABSENT** | NO | Badami_Caves_Guide.pdf p.2 |
| Q15 | arm_10 | 5 | `1eb060c8-0374-4e63-b4ad-6366ce160267` | `1eb060c8-0374-4e63-b4ad-6366ce160267` | YES | YES | YES | Pattadakal_UNESCO_Guide.pdf p.1 |
| Q18 | arm_15 | 1 | `b0a48b5a-35a0-4ff6-834c-6fa436eebead` | `35e88269-3850-4e45-b4dd-e19a41dc7d5a` | **MISMATCH** | **ABSENT** | NO | Aihole_Heritage_Guide.pdf p.2 |
| Q18 | arm_15 | 2 | `7c9f20a2-a5c9-41a7-9c18-86ad580b3aeb` | `9562ad24-5749-4156-ad83-62b5d266841e` | **MISMATCH** | YES | NO | Belur_Halebidu_Hoysala_Guide.pdf p.1 |
| Q18 | arm_15 | 3 | `35e88269-3850-4e45-b4dd-e19a41dc7d5a` | `7c9f20a2-a5c9-41a7-9c18-86ad580b3aeb` | **MISMATCH** | YES | NO | Aihole_Heritage_Guide.pdf p.1 |
| Q18 | arm_15 | 4 | `d0ee9b5e-f0b1-4d92-bb58-3d14214f08f8` | `b22c8669-1b07-4e2e-8c38-bd38818443c1` | **MISMATCH** | **ABSENT** | NO | Hampi_Vijayanagara_Guide.pdf p.2 |
| Q18 | arm_15 | 5 | `1eb060c8-0374-4e63-b4ad-6366ce160267` | `1eb060c8-0374-4e63-b4ad-6366ce160267` | YES | YES | YES | Pattadakal_UNESCO_Guide.pdf p.1 |
| Q18 | arm_10 | 1 | `b0a48b5a-35a0-4ff6-834c-6fa436eebead` | `35e88269-3850-4e45-b4dd-e19a41dc7d5a` | **MISMATCH** | **ABSENT** | NO | Aihole_Heritage_Guide.pdf p.2 |
| Q18 | arm_10 | 2 | `7c9f20a2-a5c9-41a7-9c18-86ad580b3aeb` | `9562ad24-5749-4156-ad83-62b5d266841e` | **MISMATCH** | YES | NO | Belur_Halebidu_Hoysala_Guide.pdf p.1 |
| Q18 | arm_10 | 3 | `35e88269-3850-4e45-b4dd-e19a41dc7d5a` | `7c9f20a2-a5c9-41a7-9c18-86ad580b3aeb` | **MISMATCH** | YES | NO | Aihole_Heritage_Guide.pdf p.1 |
| Q18 | arm_10 | 4 | `d0ee9b5e-f0b1-4d92-bb58-3d14214f08f8` | `b22c8669-1b07-4e2e-8c38-bd38818443c1` | **MISMATCH** | **ABSENT** | NO | Hampi_Vijayanagara_Guide.pdf p.2 |
| Q18 | arm_10 | 5 | `bc3dbadb-1ae1-4687-8265-d0766c12e521` | `bc3dbadb-1ae1-4687-8265-d0766c12e521` | YES | YES | YES | Hampi_Vijayanagara_Guide.pdf p.2 |
