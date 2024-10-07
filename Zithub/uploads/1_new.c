#include <stdio.h>
#include <pthread.h>
#include <semaphore.h>
#include <unistd.h>

#define NUM_THREADS 5

// Shared resource
int shared_counter = 0;

// Semaphore
sem_t semaphore;

// Function to be executed by each thread

void* thread_function(void* arg) {
    int thread_id = *((int*)arg);

    printf("Thread %d: Waiting to enter critical section...\n", thread_id);

    // Wait (P) operation on the semaphore
    sem_wait(&semaphore);

    // Critical section starts
    printf("Thread %d: Entered critical section.\n", thread_id);
    shared_counter++;
    printf("Thread %d: Updated shared_counter to %d\n", thread_id, shared_counter);
    
    // Simulate some work with sleep
    sleep(1);

    // Critical section ends
    printf("Thread %d: Leaving critical section.\n", thread_id);

    // Signal (V) operation on the semaphore
    sem_post(&semaphore);

    return NULL;
}

int main() {
    pthread_t threads[NUM_THREADS];
    int thread_ids[NUM_THREADS];

    // Initialize semaphore with an initial value of 1 (binary semaphore)
    sem_init(&semaphore, 0, 1);

    // Create threads
    for (int i = 0; i < NUM_THREADS; i++) {
        thread_ids[i] = i + 1;
        pthread_create(&threads[i], NULL, thread_function, &thread_ids[i]);
    }

    // Wait for all threads to finish
    for (int i = 0; i < NUM_THREADS; i++) {
        pthread_join(threads[i], NULL);
    }

    // Destroy the semaphore
    sem_destroy(&semaphore);

    // Final value of the shared variable
    printf("Final value of shared_counter: %d\n", shared_counter);

    return 0;
}