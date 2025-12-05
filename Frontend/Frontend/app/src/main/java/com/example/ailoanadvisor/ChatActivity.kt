package com.example.ailoanadvisor

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.speech.RecognizerIntent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.isVisible
import androidx.recyclerview.widget.LinearLayoutManager
import com.example.ailoanadvisor.databinding.ActivityChatBinding

class ChatActivity : AppCompatActivity() {

    private lateinit var binding: ActivityChatBinding
    private lateinit var adapter: SimpleChatAdapter
    private val messageList = ArrayList<String>()

    // ✅ Voice Input Result
    private val speechResultLauncher =
        registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
            if (result.resultCode == Activity.RESULT_OK) {
                val data =
                    result.data?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)
                binding.etMessage.setText(data?.get(0) ?: "")
            }
        }

    // ✅ Document Picker
    private val documentPickerLauncher =
        registerForActivityResult(ActivityResultContracts.GetContent()) { uri ->
            if (uri != null) {
                // On first interaction, hide the FAQ view and show the chat RecyclerView
                if (binding.faqLayout.isVisible) {
                    binding.faqLayout.isVisible = false
                    binding.recyclerView.isVisible = true
                }

                messageList.add("You: (Attached a document)")
                messageList.add("Bot: Thanks for the document, I will review it shortly. ✅")
                adapter.notifyItemRangeInserted(messageList.size - 2, 2)
                binding.recyclerView.scrollToPosition(messageList.size - 1)
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        binding = ActivityChatBinding.inflate(layoutInflater)
        setContentView(binding.root)

        adapter = SimpleChatAdapter(messageList)
        binding.recyclerView.layoutManager = LinearLayoutManager(this)
        binding.recyclerView.adapter = adapter

        // The chat view is hidden initially; the welcome/FAQ view is shown.
        binding.recyclerView.isVisible = false

        // ✅ FAQ Click Auto-Type (UPDATED)
        binding.faq1.setOnClickListener {
            startActivity(Intent(this, EligibilityActivity::class.java))
        }

        binding.faq2.setOnClickListener {
            autoAsk("Current loan interest rates")
        }

        binding.faq3.setOnClickListener {
            autoAsk("Documents required for loan")
        }

        // ✅ Send Button
        binding.btnSend.setOnClickListener {
            val msg = binding.etMessage.text.toString().trim()
            if (msg.isNotEmpty()) {
                // On first message, hide the FAQ view and show the chat RecyclerView
                if (binding.faqLayout.isVisible) {
                    binding.faqLayout.isVisible = false
                    binding.recyclerView.isVisible = true
                }
                sendMessage(msg)
            }
        }

        // ✅ Document Attach
        binding.btnAttach.setOnClickListener {
            documentPickerLauncher.launch("*/*")
        }

        // ✅ Voice Input
        binding.btnMic.setOnClickListener {
            val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(
                    RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                    RecognizerIntent.LANGUAGE_MODEL_FREE_FORM
                )
            }
            speechResultLauncher.launch(intent)
        }
    }

    private fun autoAsk(text: String) {
        binding.etMessage.setText(text)
    }

    private fun sendMessage(message: String) {
        messageList.add("You: $message")
        messageList.add("Bot: Processing your query ✅")
        binding.etMessage.text.clear()
        adapter.notifyItemRangeInserted(messageList.size - 2, 2)
        binding.recyclerView.scrollToPosition(messageList.size - 1)
    }
}
