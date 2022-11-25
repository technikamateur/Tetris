/* This should manage threads and core.*/
#ifndef CTMANAGE_H
#define CTMANAGE_H
#include <pthread.h>
extern void CTM_Add_Thread(pthread_t thread_handle);
extern pthread_t CTM_Fetch_Thread(void);
#endif
